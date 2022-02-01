export const CHAT_CHANNEL = "chat"


export function waitForAllICE(peerConnection) {
    return waitForEvent((fulfill) => {
        peerConnection.onicecandidate = (iceEvent) => {
            if (iceEvent.candidate === null) {
                fulfill()
            }
        }
    })
}


export function waitForEvent(user_function, delay=30000) {
    return new Promise((fulfill, reject) => {
        user_function(fulfill)
        setTimeout(() => reject("Waited too long"), delay)
    })
}

export function addConnectionStateHandler(peerConnection) {
    peerConnection.onconnectionstatechange = function (event) {
        console.log("onconnectionstatechange ", event.type, " is ", peerConnection.connectionState)
    };

    peerConnection.onsignalingstatechange = function (event) {
        console.log("onsignalingstatechange ", peerConnection.signalingState)
    };
    peerConnection.onicecandidateerror = function (event) {
        console.log("onicecandidateerror", event)
    };
}
