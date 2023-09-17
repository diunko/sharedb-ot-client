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

}

var ReconnectingWebSocket = require('reconnecting-websocket');

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
    S.run().catch((error)=>{
        console.log('main got error', error)
    }).finally(() => {
        console.log("exit")
        process.exit(0)
    })
}

main()
