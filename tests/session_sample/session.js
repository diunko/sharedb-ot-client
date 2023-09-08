var http = require('http');
var express = require('express');
var ShareDB = require('sharedb');
var ShareDBClient = require('sharedb/lib/client');

var richText = require('rich-text');
var WebSocket = require('ws');
var WebSocketJSONStream = require('@teamwork/websocket-json-stream');
// const {Delta} = require('rich-text');
var diff = require("diff");

let socketId = 0

class WSLogged extends WebSocketJSONStream {

    constructor(ws) {
        super(ws)
        this.socketId = socketId++

        // this.ws.addEventListener('message', ({data}) => {
        //     console.log('<<<<<<<<<<<<<<<', this.socketId)
        //     console.log(data)
        //     console.log('--------------')
        // })
    }

    push(chunk, encoding) {
        console.log('<<<<<<<<<<<<<<<', this.socketId)
        console.log(chunk)
        console.log('--------------')
        return super.push(chunk, encoding)
    }

    _send(json, callback) {
        console.log('>>>>>>>>>>>>>>>', this.socketId)
        console.log(json)
        console.log('--------------')
        return super._send(json, callback)
    }
}

let debug = false

// const axios = require('axios')
// const {assert} = require("assert");

ShareDB.types.register(richText.type);

class SandboxAPI {

    constructor(host, port) {
        this.host = host || 'localhost'
        this.port = port || 8080
        this.backend = new ShareDB()
    }

    async run() {
        console.log('SandboxAPI running')
        var self = this
        await this.createDocs()
        this.main.on('op', (ops, source) => {
            console.log('main.on.op(ops,source)', ops, source)
        })
        await this.startServer()
    }

    async setMainText(t) {
        var l = this.main.data.length()
        if (0 < l) {
            this.main.submitOp([{'delete': l}])
        }
        this.main.submitOp([{'insert': t}])
    }

    async startServer() {
        var self = this;
        var app = this.app = express();
        var server = this.server = http.createServer(app);
        var wss = this.wss = new WebSocket.Server({server: server});
        wss.on('connection', (ws) => {
            // var stream = new WebSocketJSONStream(ws);
            var stream = new WSLogged(ws);
            self.backend.listen(stream);
        });

        this.server.listen(this.port, this.host);
        console.log(`Listening on http://${this.host}:${this.port}`);
        await new Promise((done) => {
            console.log('setting INT handler')
            const handler = () => {
                console.log('got signal')
                self.server.close()
                process.removeListener('SIGINT', handler)
                process.removeListener('SIGTERM', handler)
                done()
            }
            process.on('SIGINT', handler)
            process.on('SIGTERM', handler)
        })
    }

    async createDoc(name) {
        var self = this
        return new Promise((done, fail) => {
            var connection = self.backend.connect()
            var doc = connection.get('examples', name)
            doc.fetch(function (err) {
                if (err) {
                    fail(err)
                    return;
                }
                done(doc)
            })
        })
    }

    async createDocs() {
        let main = this.main = await this.createDoc('main')
        let chat = this.chat = await this.createDoc('chat')

        if (main.type === null) {
            await new Promise((done, fail) => {
                main.create([{insert: '\n'}], 'rich-text', () => {
                    console.log('guides subscribed')
                    main.subscribe(done)
                })
            })
        }

        if (chat.type === null) {
            await new Promise((done, fail) => {
                let chatInitialValue = {
                    documentInfo: {
                        evaluations: 0,
                        reset: 0,
                        loading: false,
                        evaluation: {},
                    },
                    improvements: []
                }
                chat.create(
                    chatInitialValue,
                    'json0', () => {
                        console.log('chat subscribed')
                        chat.subscribe(done)
                    })
            })
            chat.subscribe((err) => {
                if (err) throw err;
                chat.on('op', (op, source) => {
                    console.log('chat.on.op(op,source)', op, source)
                })
            });
        }
    }
}

var ReconnectingWebSocket = require('reconnecting-websocket');

class TestClient {
    constructor(host, port) {
        // this.socket = new WebSocket('ws://' + host + ':' + port)
        this.socket = new ReconnectingWebSocket('ws://' + host + ':' + port, null, {WebSocket: WebSocket})

        this.sharedb = new ShareDBClient.Connection(this.socket)

        this.main = this.sharedb.get('examples', 'main')
        this.chat = this.sharedb.get('examples', 'chat')
    }

    subscribeThings() {
        let self = this
        this.main.subscribe(function (err) {
            self.main.on('op', function (op, source) {
                console.log('client.main.on.op(op,source)', op, source)
            });
        });

        this.chat.subscribe(function (err) {
            if (err) throw err;
            self.chat.on('op', function (op, source) {
                console.log("client.chat.on.op", op, source)
            })
        });

    }

    async run() {
        this.subscribeThings()
        console.log('sleeping')
        await sleep(1000)
        console.log('trying to submit an op')
        // this.main.submitOp([{'insert': 'testing'}])
        this.chat.submitOp([{p: ['testing'], oi: 123123}])
        while (true) {
            this.chat.submitOp([{p: ['testing'], na: 1}])
            await sleep(5000)
        }
    }
}


function sleep(time) {
    return new Promise(resolve => setTimeout(resolve, time));
}

function deepcopy(obj) {
    return JSON.parse(
        JSON.stringify(obj)
    )
}

function main() {
    // let port = Math.floor(Math.random() * 10000 + 10000)
    let port = 17171
    let host = 'localhost'
    let S = new SandboxAPI(host, port)
    S.run().finally(() => {
        console.log("exit")
        process.exit(0)
    })

    let C = new TestClient(host, port)
    C.run()
}

main()
