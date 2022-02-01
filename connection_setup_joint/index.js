import * as common from './common.js';
console.log("\n".repeat(10))

async function start() {
    const [peerConnection, dataChannel] = initializeBeforeCreatingOffer()
    await prepareOfferSDP(peerConnection)

    const remoteOfferString = prompt("Peer offer (skip if impolite peer)");
    if (remoteOfferString) {
        await bePolite(remoteOfferString, peerConnection)
    } else {
        await beImpolite(peerConnection, dataChannel)
    }
}

function initializeBeforeCreatingOffer() {
    const peerConnection = new RTCPeerConnection()
    common.addConnectionStateHandler(peerConnection)
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
    console.log("localOfferWithICECandidates:")
    console.log(JSON.stringify(localOfferWithICECandidates))
}

async function bePolite(remoteOfferString, peerConnection) {
    await receiveOfferSDP(peerConnection, remoteOfferString)
    await sendAnswerSDP(peerConnection)

    const dataChannel = await waitForDataChannel(peerConnection)
    console.log("Sending message, check the other tab")
    dataChannel.send("World")
}

async function receiveOfferSDP(peerConnection, remoteOfferString) {
    const remoteOffer = new RTCSessionDescription(JSON.parse(remoteOfferString))
    await peerConnection.setRemoteDescription(remoteOffer)
}

async function sendAnswerSDP(peerConnection) {
    const localAnswer = await peerConnection.createAnswer()
    peerConnection.setLocalDescription(localAnswer)
    await common.waitForAllICE(peerConnection)
    const localAnswerWithICECandidates = peerConnection.localDescription
    console.log("localAnswerWithICECandidates:")
    console.log(JSON.stringify(localAnswerWithICECandidates))
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

async function beImpolite(peerConnection, dataChannel) {
    await receiveAnswerSDP(peerConnection)
    await sendMessage(dataChannel)
}

async function receiveAnswerSDP(peerConnection) {
    console.log("Will wait for answer")
    const remoteAnswerString = prompt("Peer answer");
    const remoteAnswer = JSON.parse(remoteAnswerString)
    peerConnection.setRemoteDescription(remoteAnswer)
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

start()