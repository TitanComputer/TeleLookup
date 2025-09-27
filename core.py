# ---------- count total lines ----------
def count_lines_fast(filename):
    with open(filename, "rb") as f:
        return sum(buf.count(b"\n") for buf in iter(lambda: f.read(1024 * 1024), b""))


def process_chunk(chunk, parse_line, append, add, id_q, user_q, phone_q, seen_ids, results_list):
    for line in chunk:
        parsed = parse_line(line)
        if not parsed:
            continue
        if id_q and id_q not in parsed["id"]:
            continue
        if user_q and user_q not in parsed["username"].lower():
            continue
        if phone_q and phone_q not in parsed["phone"]:
            continue
        pid = parsed["id"]
        if pid not in seen_ids:
            add(pid)
            append(parsed)
