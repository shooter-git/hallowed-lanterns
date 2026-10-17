# Sessions: the music, edited in HO[LO] Desk

Each `<piece>.holo.json` here is a piece's score as a [HO[LO] Desk](https://github.com/shooter-git/holo-desk)
session. HO[LO] Desk is a studio in the browser where the notes can be played, heard and changed.

The round trip:

1. The Hallowed Lanterns adapter (kept in HO[LO] Desk's `local/` folder, on this machine only) writes a piece here from its `score()`: `node local/hallowed-lanterns/hl-export.mjs snow`
   in holo-desk.
2. The studio opens it (Songs → From your creations), and you edit it there.
3. **Send to hallowed-lanterns** in the studio writes it back here.
4. `python3 tools/audio/render.py music:snow` renders the piece. Every track the studio marks
   `"edited": true` plays its notes from this file in place of the code's (`hlaudio/session.py`). Every
   other voice, and all of the sound (instruments, stage, halls, mastering), still comes from the code.

Exporting again brings the code's latest notes into the session while keeping the tracks edited in
HO[LO]. Delete a session (or turn a track's `edited` off) to go back to the code's own notes.
