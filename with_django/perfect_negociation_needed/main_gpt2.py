# main.py
import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional

from aiortc import RTCPeerConnection, RTCSessionDescription

# ----------------- Settings -----------------
MAX_EXCHANGES = 5           # number of ping/pong pairs
CHANNEL_LABEL = "images"    # negotiated channel label
CHANNEL_ID = 0              # negotiated channel id

# ----------------- Session file helpers -----------------
def session_paths(session: str):
    base = Path(".")
    return {
        "lock":   base / f"{session}.lock",
        "offer":  base / f"{session}.offer.json",
        "answer": base / f"{session}.answer.json",
    }

async def write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path)

async def wait_for_file(path: Path, timeout: Optional[float] = None, poll=0.2) -> dict:
    start = time.time()
    last_err = None
    while True:
        if path.exists():
            try:
                text = path.read_text()
                data = json.loads(text)
                path.unlink(missing_ok=True)  # consume once
                return data
            except Exception as e:
                last_err = e
        await asyncio.sleep(poll)
        if timeout and (time.time() - start) > timeout:
            raise TimeoutError(f"Timed out waiting for {path} (last_err={last_err})")

def elect_initiator(lock_path: Path) -> bool:
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            f.write(str(os.getpid()))
        return True
    except FileExistsError:
        return False

# ----------------- WebRTC core -----------------
def make_pc(stun_url: Optional[str]) -> RTCPeerConnection:
    ice = [{"urls": [stun_url]}] if stun_url else []
    cfg = {"iceServers": ice} if ice else None
    return RTCPeerConnection(configuration=cfg)

def negotiated_dc(pc: RTCPeerConnection, label=CHANNEL_LABEL, id_=CHANNEL_ID):
    return pc.createDataChannel(label, negotiated=True, id=id_)

async def gather_local_desc(pc: RTCPeerConnection, kind: str) -> dict:
    if kind == "offer":
        await pc.setLocalDescription(await pc.createOffer())
    elif kind == "answer":
        await pc.setLocalDescription(await pc.createAnswer())
    else:
        raise ValueError("kind must be 'offer' or 'answer'")
    # short non-trickle wait to collect some ICE candidates
    await asyncio.sleep(1.0)
    ld = pc.localDescription
    return {"type": ld.type, "sdp": ld.sdp}

# ----------------- App logic -----------------
async def run(session: str, stun_url: Optional[str], file_to_send: Optional[Path]):
    paths = session_paths(session)

    is_initiator = elect_initiator(paths["lock"])
    role = "initiator" if is_initiator else "responder"
    run_id = str(time.time())  # nonce to avoid stale cross-talk
    print(f"[{role}] session='{session}' run_id={run_id}")

    # Only the initiator clears signaling files for a fresh run
    if is_initiator:
        paths["offer"].unlink(missing_ok=True)
        paths["answer"].unlink(missing_ok=True)

    # Build peer + channel
    pc = make_pc(stun_url)
    dc = negotiated_dc(pc)

    # state for ping/pong
    state = {
        "seq": 0,                    # last ping sent by initiator
        "exchanges": 0,              # completed ping→pong pairs
        "closed": False
    }

    async def graceful_close():
        if not state["closed"]:
            state["closed"] = True
            # give a moment for any final console output
            await asyncio.sleep(0.3)
            await pc.close()
            if is_initiator:
                paths["lock"].unlink(missing_ok=True)
            print(f"[{role}] closed")

    def send_json(obj: dict):
        if dc.readyState == "open":
            dc.send(json.dumps(obj))

    @dc.on("open")
    def _on_open():
        print(f"[{role}] datachannel open")
        # greet
        send_json({"type": "hello", "role": role, "run": run_id})
        # initiator sends an optional file then starts ping/pong
        if is_initiator:
            if file_to_send and file_to_send.exists():
                payload = file_to_send.read_bytes()
                print(f"[{role}] sending {file_to_send.name} ({len(payload)} bytes)")
                dc.send(payload)
            # start ping/pong
            state["seq"] = 1
            print(f"[{role}] -> ping {state['seq']}")
            send_json({"type": "ping", "seq": state["seq"]})

    @dc.on("message")
    def _on_message(msg):
        # binary payload (e.g., image bytes)
        if isinstance(msg, bytes):
            print(f"[{role}] received {len(msg)} bytes")
            return

        # textual JSON control messages
        try:
            obj = json.loads(msg)
        except Exception:
            print(f"[{role}] received text: {msg}")
            return

        typ = obj.get("type")
        if typ == "hello":
            print(f"[{role}] received hello from {obj.get('role')}, run={obj.get('run')}")
        elif typ == "ping":
            seq = obj.get("seq")
            print(f"[{role}] <- ping {seq}")
            # respond with pong
            send_json({"type": "pong", "seq": seq})
            print(f"[{role}] -> pong {seq}")
        elif typ == "pong":
            seq = obj.get("seq")
            print(f"[{role}] <- pong {seq}")
            if is_initiator:
                # one exchange completed
                state["exchanges"] += 1
                if state["exchanges"] >= MAX_EXCHANGES:
                    print(f"[{role}] exchanges done ({state['exchanges']}). Sending bye.")
                    send_json({"type": "bye"})
                    # close after a short delay to flush outbound
                    asyncio.create_task(graceful_close())
                else:
                    # send next ping
                    state["seq"] += 1
                    print(f"[{role}] -> ping {state['seq']}")
                    send_json({"type": "ping", "seq": state["seq"]})
        elif typ == "bye":
            print(f"[{role}] received bye; closing.")
            asyncio.create_task(graceful_close())
        else:
            print(f"[{role}] received: {obj}")

    try:
        if is_initiator:
            local_offer = await gather_local_desc(pc, "offer")
            await write_json(paths["offer"], {"sdp": local_offer, "run": run_id})
            print(f"[{role}] wrote {paths['offer'].name}; waiting for {paths['answer'].name} ...")

            ans = await wait_for_file(paths["answer"], timeout=90)
            if ans.get("run") != run_id:
                raise RuntimeError("Stale/mismatched answer detected")
            await pc.setRemoteDescription(RTCSessionDescription(**ans["sdp"]))
            print(f"[{role}] setRemoteDescription(answer) ✓")

        else:
            print(f"[{role}] waiting for {paths['offer'].name} ...")
            off = await wait_for_file(paths["offer"], timeout=90)
            await pc.setRemoteDescription(RTCSessionDescription(**off["sdp"]))
            print(f"[{role}] setRemoteDescription(offer) ✓")

            local_answer = await gather_local_desc(pc, "answer")
            await write_json(paths["answer"], {"sdp": local_answer, "run": off.get("run")})
            print(f"[{role}] wrote {paths['answer'].name}")

        # Keep the process alive long enough for pings/pongs (or earlier close)
        # If nothing happens (e.g., channel never opens), we time out.
        try:
            await asyncio.sleep(20)
        finally:
            await graceful_close()

    except Exception as e:
        print(f"[{role}] error: {e}")
        await graceful_close()

# ----------------- CLI -----------------
def parse_args():
    ap = argparse.ArgumentParser(description="Role-less WebRTC (file signaling) with ping/pong")
    ap.add_argument("--stun", default=None,
                    help="Optional STUN URL, e.g. stun:stun.l.google.com:19302")
    ap.add_argument("--send", type=Path, default=None,
                    help="Optional path to a file to send (initiator only)")
    ap.add_argument("--session", default="session",
                    help="Session namespace (default: 'session')")
    return ap.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.session, args.stun, args.send))
