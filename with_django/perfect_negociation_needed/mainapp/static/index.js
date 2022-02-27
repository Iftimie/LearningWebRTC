import * as common from './common.js';
console.log("\n".repeat(10))

export async function start(username) {
    const [peerConnection, dataChannel] = initializeBeforeCreatingOffer(username)
    withPerfectNegociationHandler(async sessionDescriptionProtocol => {
        if (sessionDescriptionProtocol.type === "offer") {
            await beCallee(sessionDescriptionProtocol, peerConnection, username, dataChannel)
        } else {
            await beCaller(sessionDescriptionProtocol, peerConnection, dataChannel)
        }
    }, peerConnection, username, dataChannel)

    firstNegotiationNeededEvent(peerConnection, dataChannel)

    if (username === "impolite") {
        // for the sake of being able to track what's happening, only the impolite peer will add video tracks
        await sleep(5000)
        secondNegotiationNeededEvent(peerConnection)
    }
}

function initializeBeforeCreatingOffer(username) {
    const peerConnection = { obj: initializeRTCPeerConnection(username) }
    const dataChannel = { obj: null }
    return [peerConnection, dataChannel]
}

function initializeRTCPeerConnection(username) {
    const peerConnection = new RTCPeerConnection()
    common.addConnectionStateHandler(peerConnection, username)
    peerConnection.ontrack = (ev) => {
        console.log("received track")
    }
    return peerConnection
}

async function beCallee(remoteOffer, peerConnection, username, dataChannel) {
    await receiveOfferSDP(peerConnection, remoteOffer)
    await sendAnswerSDP(peerConnection, username)

    try {
        // the new datachannel can happen earlier than the call to waitForDataChannel, so this waiting won't catch any event and it can result in timeout
        dataChannel.obj = await waitForDataChannel(peerConnection)
    } catch (err) {
        console.log("waited too long for data channel. probably it was already received")
    } finally {
        dataChannel.obj.send("World")
        console.log("Sending message, check the other tab")
    }
}


async function receiveOfferSDP(peerConnection, remoteOffer) {
    await peerConnection.obj.setRemoteDescription(remoteOffer)

}

async function sendAnswerSDP(peerConnection, username) {
    // not necessary in this particular scenario to collect ICE candidates for answer
    // to establish connection is sufficient from the caller to send his ICE candidates in the offer
    console.log("Sending answer")
    await peerConnection.obj.setLocalDescription()
    // await common.waitForAllICE(peerConnection)
    const localAnswerWithICECandidates = peerConnection.obj.localDescription
    await fetch('http://127.0.0.1:10000/sdp', {
        method: 'POST',
        body: JSON.stringify({ "user": username, "sdp": localAnswerWithICECandidates }),
        redirect: 'manual',
    })
}

function waitForDataChannel(peerConnection) {
    return common.waitForEvent((fulfill) => {
        peerConnection.obj.ondatachannel = function (e) {
            const dataChannel = e.channel
            console.log("Received datachannel")
            dataChannel.onmessage = function (e) {
                console.log("Received message: ", e.data)
            };
            fulfill(dataChannel)
        }
    })
}

async function beCaller(remoteAnswer, peerConnection, dataChannel) {
    await receiveAnswerSDP(peerConnection, remoteAnswer)
    await sendMessage(dataChannel)
}

async function receiveAnswerSDP(peerConnection, remoteAnswer) {
    await peerConnection.obj.setRemoteDescription(remoteAnswer)
}

async function sendMessage(dataChannel) {
    if (secondOfferIsJustWithVideoTracks(dataChannel))
        await waitForDataChannelOpen(dataChannel)
    console.log("Sending message. Check the other tab")
    dataChannel.obj.send("Hello")
}

function secondOfferIsJustWithVideoTracks(dataChannel) {
    // When the current role is impolite, and it is caller, it will make two offers.
    // first just with a datachannel, and it's necessary to wait for it to be open
    // second with a new datachannel, that is simply ignored, and with tracks. but during this second time it's not necessary for the first datachannel to be open, because it already is
    return dataChannel.obj !== null && dataChannel.obj.readyState !== "open"
}

function waitForDataChannelOpen(dataChannel) {
    return common.waitForEvent((fulfill) => {
        dataChannel.obj.onopen = function () {
            if (dataChannel.obj.readyState == "open") {
                fulfill()
            }
        };
    })
}

function withPerfectNegociationHandler(user_function, peerConnection, username, dataChannel) {
    var makingOffer = { obj: false }

    addNegotiationNeededHandler(peerConnection, makingOffer, username)

    var es = new ReconnectingEventSource('/events?channel=testchannel');
    es.addEventListener('message', async function ({ data }) {
        try {
            if (shouldSkipMessage(data, peerConnection, username, makingOffer)) {
                return;
            }
            if (peerRefreshedPage(dataChannel) || shouldAcceptOffer(username, peerConnection)) {
                console.log("Reinitialized RTCPeerConnection")
                peerConnection.obj.close()
                peerConnection.obj = initializeRTCPeerConnection()
                addNegotiationNeededHandler(peerConnection, makingOffer, username)
            }

            const SDP = JSON.parse(data).sdp
            await user_function(SDP)
        } catch (err) {
            console.error(err);
        }
    }, false);
    return makingOffer
}

function shouldAcceptOffer(username, peerConnection) {
    if (username == "polite" && peerConnection.obj.connectionState === "new")
        return true
    return false
}

function shouldSkipMessage(data, peerConnection, username, makingOffer) {
    const message = JSON.parse(data)
    if (messageIsReflected(message, username)) {
        return true;
    }
    const description = message.sdp

    if (shouldIgnoreOffer(description, makingOffer, peerConnection, username)) {
        return true;
    }
    return false
}

function messageIsReflected(message, username) {
    // Because of the chosen simplification, both peers are subscribed to the same channel.
    // Thus, messages are pushed back to the sender and we want to skip them.
    return message.user === username
}

function shouldIgnoreOffer(description, makingOffer, peerConnection, username) {
    const offerCollision = (description.type === "offer") && (makingOffer.obj || peerConnection.obj.signalingState !== "stable")
    const shouldIgnore = (username === "impolite") && offerCollision;
    return shouldIgnore
}

function peerRefreshedPage(dataChannel) {
    // it can also be in state new. this time it's necessary to check more explicitly because we can receive a new offer containing video tracks without the other peer refreshing the page
    return dataChannel.obj !== null && (dataChannel.obj.readyState === "closing" || dataChannel.obj.readyState === "closed")
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function addNegotiationNeededHandler(peerConnection, makingOffer, username) {
    var collectedIce = false
    peerConnection.obj.onnegotiationneeded = async () => {
        try {
            makingOffer.obj = true
            await peerConnection.obj.setLocalDescription()
            if (!collectedIce) {
                await common.waitForAllICE(peerConnection)
                collectedIce = true
            }

            const localOfferWithICECandidates = peerConnection.obj.localDescription
            await fetch('http://127.0.0.1:10000/sdp', {
                method: 'POST',
                body: JSON.stringify({ "user": username, "sdp": localOfferWithICECandidates })
            })
        } catch (err) {
            console.log(err)
        } finally {
            makingOffer.obj = false
        }
    }
}

async function secondNegotiationNeededEvent(peerConnection) {
    // no negociationneeded event will be triggered for a new data channel, however I will still send it just to not update the callee branch
    // the callee branch always expects a new data channel (waitForDataChannel)
    peerConnection.obj.createDataChannel("chat2")

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
    for (const track of stream.getTracks()) {
        peerConnection.obj.addTrack(track, stream);
    }
    console.log("Should fire new negociationneeded event")
}

function firstNegotiationNeededEvent(peerConnection, dataChannel) {
    // will trigger negotiationneeded event
    dataChannel.obj = peerConnection.obj.createDataChannel(common.CHAT_CHANNEL)
    dataChannel.obj.onmessage = function (e) {
        console.log("Received message: ", e.data)
    };
}