#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, redirect
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()

    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        # self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        # self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())

    def world(self):
        return self.space

myWorld = World()

class Listener:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()

def set_listener( entity, data ):
    ''' do something with the update ! '''


myWorld.add_set_listener( set_listener )

listeners = list()

@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return redirect("/static/index.html", code=302)

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLE-MENT ME
    try:
        while True:
            msg = ws.receive()
            if (msg is not None):
                packet = json.loads(msg)
                myWorld.set(packet.get("entity"), packet.get("data"))
                for listener in listeners:
                    listener.put(msg)
            else:
                break
    except:
        '''Do nothing'''
    return None

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    listener = Listener()
    listeners.append(listener)
    g = gevent.spawn(read_ws, ws, listener)
    try:
        while True:
            msg = listener.get()
            ws.send(msg)
    except Exception as e:# WebSocketError as e:
        print "WS Error %s" % e
    finally:
        listeners.remove(listener)
        gevent.kill(g)


def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    myWorld.set(entity, json.loads(request.data))
    return (json.dumps(myWorld.get(entity)), 200, {'ContentType':'application/json'})

@app.route("/world", methods=['POST','GET'])
def world():
    '''you should probably return the world here'''
    if request.method == 'POST':
        worldChanges = json.loads(request.data)
        [(lambda point: myWorld.set(myWorld.getNewEntityName(), point))(point) for point in worldChanges]
    return json.dumps(myWorld.world()), 200, {'ContentType':'application/json'}

@app.route("/entity/<entity>")
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return (json.dumps(myWorld.get(entity)), 200, {'ContentType':'application/json'})

@app.route("/clear", methods=['POST','GET'])
def clear():
    myWorld.clear()
    return json.dumps(myWorld.world()), 200, {'ContentType':'application/json'}



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
