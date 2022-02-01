export const CHAT_CHANNEL = "chat"


export function waitForAllICE(peerConnection) {
    return waitForEvent((fulfill) => {
        peerConnection.onicecandidate = (iceEvent) => {
            if (iceEvent.candidate === null) fulfill()
        }
    })
}

export function waitForEvent(user_function) {
    return new Promise((fulfill, reject) => {
        user_function(fulfill)
        setTimeout(() => reject("Waited too long"), 60000)
    })
}

export function addConnectionStateHandler(peerConnection, username) {
    window.onbeforeunload = function() {
        retrieveOffer(username) 
    }
    peerConnection.onconnectionstatechange = function () {
        var state = peerConnection.connectionState;
        console.log(state)
        if (state === "disconnected" || state === "failed") {
            retrieveOffer(username)
        } else if (state === "connected") {
            clearBothOffers()
        }
    };
}

function clearBothOffers() {
    fetch('http://127.0.0.1:10000/clear', { method: 'POST'})
}

function retrieveOffer(username) {
    fetch('http://127.0.0.1:10000/offer', { method: 'POST', body: JSON.stringify({"user": username, "offer": ''})})
}