import aiortc
import asyncio
import common
import asyncio
import requests
import json
from aiosseclient import aiosseclient

async def main():
    username = "impolite"
    peerConnection, dataChannel = initializeBeforeCreatingOffer(username)

    async def inner(sessionDescriptionProtocol):
        if (sessionDescriptionProtocol.type == "offer"):
            await beCallee(sessionDescriptionProtocol, peerConnection, username, dataChannel)
        else:
            await beCaller(sessionDescriptionProtocol, peerConnection, dataChannel)

    withPerfectNegociationHandler(inner, peerConnection, username, dataChannel)
    await firstNegotiationNeededEvent(peerConnection, dataChannel)

    await asyncio.sleep(100000)

def initializeBeforeCreatingOffer(username):
    peerConnection = {'obj': None, 'negociate': None}
    peerConnection['obj'] = initializeRTCPeerConnection(username)
    dataChannel = {'obj': None}
    return peerConnection, dataChannel


def initializeRTCPeerConnection(username):
    peerConnection = aiortc.RTCPeerConnection()
    common.addConnectionStateHandler(peerConnection, username)
    @peerConnection.on('track')
    def ontrack(track):
        print("received track")
    return peerConnection


async def beCallee(remoteOffer, peerConnection, username, dataChannel):
    # the callee always expects a new data channel.
    await receiveOfferSDP(peerConnection, remoteOffer)
    await sendAnswerSDP(peerConnection, username)

    try:
        # the new datachannel can happen earlier than the call to waitForDataChannel, so this waiting won't catch any event and it can result in timeout
        dataChannel['obj'] = await waitForDataChannel(peerConnection)
    except:
        print("waited too long for data channel. probably it was already received asynchronously")
    finally:
        dataChannel['obj'].send("World")
        print("Sending message, check the other tab")


async def receiveOfferSDP(peerConnection, remoteOffer):
    await peerConnection['obj'].setRemoteDescription(remoteOffer)


async def sendAnswerSDP(peerConnection, username):
    localAnswer = await peerConnection['obj'].createAnswer()
    await peerConnection['obj'].setLocalDescription(localAnswer)
    # no need to wait for all ICE

    localAnswerWithICECandidates = peerConnection['obj'].localDescription
    localAnswerWithICECandidatesSerializable = {
        "type": localAnswerWithICECandidates.type,
        "sdp": localAnswerWithICECandidates.sdp,
    }
    requests.post("http://127.0.0.1:10000/sdp", json.dumps({"user": username, "sdp": localAnswerWithICECandidatesSerializable}))

def waitForDataChannel(peerConnection):
    async def inner(fulfill):
        peerConnectionObj = peerConnection['obj']

        aiortc.RTCDataChannel
        @peerConnectionObj.on('datachannel')
        def ondatachannel(channel):
            channel.add_listener('message', lambda e: print(e))

            fulfill(channel)
    
    return common.waitForEvent(inner)

async def beCaller(remoteAnswer, peerConnection, dataChannel):
    await receiveAnswerSDP(peerConnection, remoteAnswer)
    await sendMessage(dataChannel)


async def receiveAnswerSDP(peerConnection, remoteAnswer):
    await peerConnection['obj'].setRemoteDescription(remoteAnswer)


async def sendMessage(dataChannel):
    if (secondOfferIsJustWithVideoTracks(dataChannel)):
        await waitForDataChannelOpen(dataChannel)
    print("Sending message. Check the other tab")
    dataChannel['obj'].send("Hello")

def secondOfferIsJustWithVideoTracks(dataChannel):
    # When the current role is impolite, and it is caller, it will make two offers.
    # first just with a datachannel, and it's necessary to wait for it to be open
    # second with a new datachannel, that is simply ignored, and with tracks. but during this second time it's not necessary for the first datachannel to be open, because it already is
    return dataChannel['obj'] != None and dataChannel['obj'].readyState != "open"

def waitForDataChannelOpen(dataChannel):
    async def inner(fulfill):
        dataChannel['obj'].add_listener('open', lambda: fulfill(None))
    
    return common.waitForEvent(inner)
    
def withPerfectNegociationHandler(user_function, peerConnection, username, dataChannel):
    makingOffer = {'obj': False}

    addNegociationNeededHandler(peerConnection, makingOffer, username)
    async def eventSource():
        events = aiosseclient('http://127.0.0.1:10000/events?channel=testchannel')
        async for event in events: 
            message = str(event)
            if message:
                if shouldSkipMessage(message, peerConnection, username, makingOffer):
                    continue

                if await peerRefreshedPage(dataChannel):
                    peerConnection['obj'].close()
                    peerConnection['obj'] = initializeRTCPeerConnection(username)
                    addNegociationNeededHandler(peerConnection, makingOffer, username)
                
                SDP = json.loads(json.loads(message)['sdp'])
                SDP = aiortc.RTCSessionDescription(**SDP)
                await user_function(SDP)
    asyncio.create_task(eventSource())


def shouldSkipMessage(data, peerConnection, username, makingOffer):
    message = json.loads(data)
    if (messageIsReflected(message, username)):
        return True

    description = json.loads(message['sdp'])

    if (shouldIgnoreOffer(description, makingOffer, peerConnection, username)):
        return True

    return False


def messageIsReflected(message, username):
    # Because of the chosen simplification, both peers are subscribed to the same channel.
    # Thus, messages are pushed back to the sender and we want to skip them.
    return message['user'] == username


def shouldIgnoreOffer(description, makingOffer, peerConnection, username):
    offerCollision = (description['type'] == "offer") and (makingOffer['obj'] or peerConnection['obj'].signalingState != "stable")
    shouldIgnore = (username == "impolite") and offerCollision
    return shouldIgnore


async def peerRefreshedPage(dataChannel):
    # aparently the aiortc API is not perfect. it does not detect that the datachannel has been closed
    try:
        if dataChannel['obj'] != None and dataChannel['obj'].readyState == "open":
            print("Aparently the only way to check if the connection is still open is by trying to send a message")
            await dataChannel['obj'].send("test message")
    except:
        return True
    return False


def addNegociationNeededHandler(peerConnection, makingOffer, username):
    # collectedIce = False # no longer needed since the API automatically gathers them during setLocalDescription
    async def inner():
        makingOffer['obj'] = True
        await peerConnection['obj'].setLocalDescription(await peerConnection['obj'].createOffer())
        localOfferWithICECandidates = peerConnection['obj'].localDescription
        localOfferWithICECandidatesSerializable = {
            "type": localOfferWithICECandidates.type,
            "sdp": localOfferWithICECandidates.sdp,
        }
        requests.post("http://127.0.0.1:10000/sdp", json.dumps({"user": username, "sdp": localOfferWithICECandidatesSerializable}))
        makingOffer['obj'] = False

    peerConnection['negociate'] = inner


async def firstNegotiationNeededEvent(peerConnection, dataChannel):
    dataChannelObj = peerConnection['obj'].createDataChannel(common.CHAT_CHANNEL)
    dataChannel['obj'] = dataChannelObj
    @dataChannelObj.on('message')
    def onmessage(msg):
        print(msg)

    @dataChannelObj.on('close')
    def onclose(msg):
        print("closed dataChannel")
    
    await peerConnection['negociate']()

asyncio.run(main())