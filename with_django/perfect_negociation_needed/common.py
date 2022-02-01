from aiortc import RTCPeerConnection
from functools import partial
import requests
from promise import Promise
import asyncio

CHAT_CHANNEL = "chat"


async def waitForEvent(user_function, timeout = 10):
    
    event = asyncio.Event()
    fulfilled_value = None
    
    def fulfill(value):
        nonlocal fulfilled_value
        fulfilled_value = value

        event.set()
    
    async def waiter():
        await event.wait()

    asyncio.create_task(user_function(fulfill))
    
    await asyncio.wait_for(waiter(), timeout=timeout)
    return fulfilled_value


def setTimeout(func, delay):
    async def inner():
        await asyncio.sleep(delay)
        func()
    asyncio.create_task(inner())


def addConnectionStateHandler(peerConnection: RTCPeerConnection, username):
    peerConnection.add_listener('iceconnectionstatechange', partial(__onIceConnectionStateChange, peerConnection, username))

def __onIceConnectionStateChange(peerConnection: RTCPeerConnection, username):
    state = peerConnection.iceConnectionState
    print(state)
    if state == "disconnected" or state == "failed":
        retrieveOffer(username)
    elif state == "connected":
        clearBothOffers(username)
