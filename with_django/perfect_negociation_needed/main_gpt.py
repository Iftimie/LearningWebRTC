# main.py
import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import BYE  # just to mirror terminology, not used
from aiortc.sdp import candidate_from_sdp

# ---------- Tiny “signaling via files” helpers ----------

SIGNAL_DIR = Path(".")
OFFER_FILE = SIGNAL_DIR / "offer.json"
ANSWER_FILE = SIGNAL_DIR / "answer.json"

async def write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path)

async def wait_for_file(path: Path, timeout: Optional[float] = None, poll=0.2) -> dict:
    start = time.time()
    while True:
        if path.exists():
            try:
                return json.loads(path.read_text())
            finally:
                # consume once
                path.unlink(missing_ok=True)
        await asyncio.sleep(poll)
        if timeout and (time.time() - start) > timeout:
            raise TimeoutError(f"Timed out waiting for {path}")

# ---------- WebRTC core ----------

def make_pc(ice_server: Optional[str]) -> RTCPeerConnection:
    ice_servers = [{"urls": [ice_server]}] if ice_server else []
    pc = RTCPeerConnection(configuration={"iceServers": ice_servers} if ice_servers else None)
    return pc

def negotiated_data_channel(pc: RTCPeerConnection, label="images", id_=0):
    """
    Create a negotiated data channel: both peers call this with same label & id.
    Avoids on('datachannel') races entirely.
    """
    dc = pc.createDataChannel(label, negotiated=True, id=id_)
    return dc

async def gather_and_serialize_local_desc(pc: RTCPeerConnection, desc_type: str) -> dict:
    # Create and set local description
    if desc_type == "offer":
        await pc.setLocalDescription(await pc.createOffer())
    elif desc_type == "answer":
        await pc.setLocalDescription(await pc.createAnswer())
    else:
        raise ValueError("desc_type must be 'offer' or 'answer'")

    # Let ICE gather for a short moment (non-trickle)
    await asyncio.sleep(1.0)
    ld = pc.localDescription
    return {"type": ld.type, "sdp": ld.sdp}

async def run_caller(stun_url: Optional[str], file_to_send: Optional[Path]):
    pc = make_pc(stun_url)
    dc = negotiated_data_channel(pc, label="images", id_=0)

    @dc.on("open")
    def _on_open():
        print("[caller] datachannel open")
        dc.send("hello from caller")
        if file_to_send and file_to_send.exists():
            payload = file_to_send.read_bytes()
            print(f"[caller] sending {file_to_send.name} ({len(payload)} bytes)")
            dc.send(payload)

    @dc.on("message")
    def _on_message(msg):
        if isinstance(msg, bytes):
            print(f"[caller] received {len(msg)} bytes")
        else:
            print(f"[caller] received: {msg}")

    # Create offer, write to file
    local_offer = await gather_and_serialize_local_desc(pc, "offer")
    await write_json(OFFER_FILE, {"sdp": local_offer})
    print("[caller] wrote offer.json; waiting for answer.json ...")

    # Wait for answer, apply
    ans = await wait_for_file(ANSWER_FILE, timeout=60)
    remote = RTCSessionDescription(**ans["sdp"])
    await pc.setRemoteDescription(remote)
    print("[caller] setRemoteDescription(answer) ✓")

    # Keep alive long enough for demo traffic
    await asyncio.sleep(10)
    await pc.close()

async def run_callee(stun_url: Optional[str]):
    pc = make_pc(stun_url)
    dc = negotiated_data_channel(pc, label="images", id_=0)

    @dc.on("open")
    def _on_open():
        print("[callee] datachannel open")
        dc.send("hello from callee")

    @dc.on("message")
    def _on_message(msg):
        if isinstance(msg, bytes):
            print(f"[callee] received {len(msg)} bytes")
        else:
            print(f"[callee] received: {msg}")

    # Wait for offer, apply
    print("[callee] waiting for offer.json ...")
    off = await wait_for_file(OFFER_FILE, timeout=60)
    remote = RTCSessionDescription(**off["sdp"])
    await pc.setRemoteDescription(remote)
    print("[callee] setRemoteDescription(offer) ✓")

    # Create answer, write to file
    local_answer = await gather_and_serialize_local_desc(pc, "answer")
    await write_json(ANSWER_FILE, {"sdp": local_answer})
    print("[callee] wrote answer.json")

    # Keep alive long enough for demo traffic
    await asyncio.sleep(10)
    await pc.close()

def parse_args():
    ap = argparse.ArgumentParser(description="Serverless WebRTC (file signaling) demo")
    ap.add_argument("--role", choices=["caller", "callee"], required=True,
                    help="caller creates offer; callee answers")
    ap.add_argument("--stun", default=None,
                    help="Optional STUN URL, e.g. stun:stun.l.google.com:19302")
    ap.add_argument("--send", type=Path, default=None,
                    help="Caller: optional path to a file (e.g., jpg) to send as bytes")
    return ap.parse_args()

if __name__ == "__main__":
    args = parse_args()
    # ensure a clean slate
    if args.role == "caller":
        ANSWER_FILE.unlink(missing_ok=True)
    elif args.role == "callee":
        # let callee consume the offer, so ensure stale answer is gone
        OFFER_FILE.unlink(missing_ok=True)

    asyncio.run(run_caller(args.stun, args.send) if args.role == "caller"
                else run_callee(args.stun))
