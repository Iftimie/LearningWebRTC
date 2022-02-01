import * as common from './common.js';
console.log("\n".repeat(10))

export async function start(username) {
    const [peerConnection, dataChannel] = initializeBeforeCreatingOffer(username)
    const localOffer = await prepareOfferSDP(peerConnection)

    const remoteOffer = await sendLocalOfferAndQueryRemoteOffer(localOffer, username)
    if (remoteOffer) {
        await beCallee(remoteOffer, peerConnection)
    } else {
        await beCaller(peerConnection, dataChannel)
    }
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

async function prepareOfferSDP(peerConnection) {
    const localOffer = await peerConnection.createOffer()
    await peerConnection.setLocalDescription(localOffer)
    await common.waitForAllICE(peerConnection)
    const localOfferWithICECandidates = peerConnection.localDescription
    return localOfferWithICECandidates
}

async function sendLocalOfferAndQueryRemoteOffer(localOffer, username) {
    const response = await fetch('http://127.0.0.1:10000/offer', { method: 'POST',
        body: JSON.stringify({ "user": username, "offer": localOffer})
    })
    const remoteOffer = (await response.json()).offer
    return remoteOffer
}

async function beCallee(remoteOfferString, peerConnection) {
    await receiveOfferSDP(peerConnection, remoteOfferString)
    await sendAnswerSDP(peerConnection)

    const dataChannel = await waitForDataChannel(peerConnection)
    console.log("Sending message, check the other tab")
    dataChannel.send("World")
}

async function receiveOfferSDP(peerConnection, remoteOffer) {
    await peerConnection.setRemoteDescription(remoteOffer)
}

async function sendAnswerSDP(peerConnection) {
    const localAnswer = await peerConnection.createAnswer()
    peerConnection.setLocalDescription(localAnswer)
    await common.waitForAllICE(peerConnection)
    const localAnswerWithICECandidates = peerConnection.localDescription
    await fetch('http://127.0.0.1:10000/answer', { method: 'POST',
        body: JSON.stringify({"answer": localAnswerWithICECandidates})
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

async function beCaller(peerConnection, dataChannel) {
    await receiveAnswerSDP(peerConnection)
    await sendMessage(dataChannel)
}

async function receiveAnswerSDP(peerConnection) {
    console.log("Will wait for answer")
    const remoteAnswer = await waitForAnswer()
    peerConnection.setRemoteDescription(remoteAnswer)
}

function waitForAnswer() {
    return common.waitForEvent((fullfill) => {
        var es = new ReconnectingEventSource('/events?channel=testchannel');
        es.addEventListener('message', function (e) {
            const remoteAnswer = JSON.parse(e.data)
            fullfill(remoteAnswer)
        }, false);
    })
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