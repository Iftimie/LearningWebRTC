export const CHAT_CHANNEL = "chat"

export function waitForAllICE(peerConnection) {
    return new Promise((fufill, reject) => {
        peerConnection.onicecandidate = (iceEvent) => {
            if (iceEvent.candidate === null) fufill()
        }
        setTimeout(() => reject("Waited too long for ice candidates"), 1000)
    }) 
  }

export function addConnectionStateHandler(peerConnection) {
    peerConnection.onconnectionstatechange = function () {
        console.log(peerConnection.connectionState)
    };
}