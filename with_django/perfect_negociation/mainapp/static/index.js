import * as common from './common.js';
console.log("\n".repeat(10))

export async function start(username) {
    const [peerConnection, dataChannel] = initializeBeforeCreatingOffer(username)
    const makingOffer = withPerfectNegociationHandler(async sessionDescriptionProtocol => {
        if (sessionDescriptionProtocol.type === "offer") {
            await beCallee(sessionDescriptionProtocol, peerConnection, username, dataChannel)
        } else {
            await beCaller(sessionDescriptionProtocol, peerConnection, dataChannel)
        }
    }, peerConnection, username)
    await sendOfferSDP(peerConnection, makingOffer, username)
}

function initializeBeforeCreatingOffer(username) {
    const peerConnection = new RTCPeerConnection()
    common.addConnectionStateHandler(peerConnection, username)
    const dataChannel = peerConnection.createDataChannel(common.CHAT_CHANNEL)
    dataChannel.onmessage = function (e) {
        console.log("Received message: ", e.data)
    };
    return [peerConnection, dataChannel]
}

async function sendOfferSDP(peerConnection, makingOffer, username) {
    try {
        makingOffer.obj = true
        await peerConnection.setLocalDescription(await peerConnection.createOffer())

        await common.waitForAllICE(peerConnection)
        const localOfferWithICECandidates = peerConnection.localDescription
        await fetch('http://127.0.0.1:10000/sdp', { method: 'POST',
            body: JSON.stringify({ "user": username, "sdp": localOfferWithICECandidates})
        })
    } catch (err) {
        console.log(err)
    } finally {
        makingOffer.obj = false
    }
}

async function beCallee(remoteOffer, peerConnection, username, dataChannel) {
    if (peerRefreshedPage(dataChannel))
        peerConnection = new RTCPeerConnection()
    await receiveOfferSDP(peerConnection, remoteOffer)
    await sendAnswerSDP(peerConnection, username)

    dataChannel = await waitForDataChannel(peerConnection)
    console.log("Sending message, check the other tab")
    dataChannel.send("World")
}

async function receiveOfferSDP(peerConnection, remoteOffer) {
    await peerConnection.setRemoteDescription(remoteOffer)
}

async function sendAnswerSDP(peerConnection, username) {
    await peerConnection.setLocalDescription(await peerConnection.createAnswer())
    await common.waitForAllICE(peerConnection)
    const localAnswerWithICECandidates = peerConnection.localDescription
    await fetch('http://127.0.0.1:10000/sdp', { method: 'POST',
        body: JSON.stringify({"user": username, "sdp": localAnswerWithICECandidates})
    })
}

function waitForDataChannel(peerConnection) {
    return common.waitForEvent((fulfill) => {
        peerConnection.ondatachannel = function (e) {
            const dataChannel = e.channel
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
    await peerConnection.setRemoteDescription(remoteAnswer)
}

async function sendMessage(dataChannel) {
    await waitForDataChannelOpen(dataChannel)
    console.log("Sending message. Check the other tab")
    dataChannel.send("Hello")
}

function waitForDataChannelOpen(dataChannel) {
    return common.waitForEvent((fulfill) => {
        dataChannel.onopen = function() {
            if (dataChannel.readyState == "open") {
                fulfill()
            }
        };
    })
}

function withPerfectNegociationHandler(user_function, peerConnection, username) {
    var makingOffer = {obj: false}
    var es = new ReconnectingEventSource('/events?channel=testchannel');
    es.addEventListener('message', async function ({data}) {
        try {
            if (shouldSkipMessage(data, peerConnection, username, makingOffer)) {
                return;
            }
            const SDP = JSON.parse(JSON.parse(data).sdp)
            await user_function(SDP)
        } catch(err) {
            console.error(err);
        }   
    }, false);
    return makingOffer
}

function shouldSkipMessage(data, peerConnection, username, makingOffer) {
    const message = JSON.parse(data)
    if (messageIsReflected(message, username)){
        return true;
    }
    const description = JSON.parse(message.sdp)

    if (shouldIgnoreOffer(description, makingOffer, peerConnection, username)){
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
    const offerCollision = (description.type === "offer") && (makingOffer.obj || peerConnection.signalingState !== "stable")
    const shouldIgnore = (username === "impolite") && offerCollision;
    return shouldIgnore
}

function peerRefreshedPage(dataChannel) {
    return dataChannel.readyState !== "open"
}