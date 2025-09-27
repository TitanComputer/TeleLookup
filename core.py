# ---------- count total lines ----------
def count_lines_fast(filename):
    with open(filename, "rb") as f:
        return sum(buf.count(b"\n") for buf in iter(lambda: f.read(1024 * 1024), b""))


# ---------- process chunk ----------
def process_chunk(chunk, parse_line, append, add, id_q, user_q, phone_q, seen_ids, results_list):
    # آماده‌سازی queryها بیرون از حلقه
    id_q = id_q or None
    user_q = user_q.lower() if user_q else None
    phone_q = phone_q or None

    local_add = add
    local_append = append
    local_seen = seen_ids

    for line in chunk:
        parsed = parse_line(line)
        if not parsed:
            continue

        pid = parsed["id"]

        if id_q and id_q not in pid:
            continue
        if user_q and user_q not in parsed["username"].lower():
            continue
        if phone_q and phone_q not in parsed["phone"]:
            continue

        if pid not in local_seen:
            local_add(pid)
            local_append(parsed)
