export const CHAT_CHANNEL = "chat"


export function waitForAllICE(peerConnection) {
    return waitForEvent((fulfill) => {
        peerConnection.onicecandidate = (iceEvent) => {
            if (iceEvent.candidate === null) 
            fulfill()
        }
    })
}


export function waitForEvent(user_function) {
    return new Promise((fulfill, reject) => {
        user_function(fulfill)
        setTimeout(() => reject("Waited too long"), 60000)
    })
}

export function addConnectionStateHandler(peerConnection) {
    peerConnection.onconnectionstatechange = function () {
        console.log(peerConnection.connectionState)
    };
}