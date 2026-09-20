import asyncio

from server.rooms import RoomHub
from server.store import Store
from server.tests.fakes import FakeLinq


def test_private_whisper_routes_to_that_dm_only():
    store = Store(":memory:")
    linq = FakeLinq()
    hub = RoomHub(store, linq)
    store.bind_chat("dm-sam", "demo", "dm", "sam")
    store.bind_chat("dm-priya", "demo", "dm", "priya")
    store.bind_chat("grp", "demo", "group", None)
    store.upsert_member("demo", "sam", "+15551111111")
    store.upsert_member("demo", "priya", "+15552222222")

    asyncio.run(hub.ingest("demo", "priya", "private:priya", "I cannot be in a room with Alex"))
    asyncio.run(hub.ingest("demo", "sam", "private:sam", "I can't do more than $150"))

    sam_msgs = [m for m in linq.sent if m["chat_id"] == "dm-sam"]
    priya_msgs = [m for m in linq.sent if m["chat_id"] == "dm-priya"]
    group_msgs = [m for m in linq.sent if m["chat_id"] == "grp"]
    assert sam_msgs, "sam should get a whisper on their DM"
    assert priya_msgs, "priya should get a whisper on their DM"
    assert not group_msgs
    assert all("Alex" not in m["text"] for m in sam_msgs)
    assert all("priya" not in m["text"].lower() for m in sam_msgs)


def test_group_inbound_is_public_and_rooms_are_isolated():
    store = Store(":memory:")
    hub = RoomHub(store, FakeLinq())
    asyncio.run(hub.ingest("alpha", "sam", "public", "alpha plan"))
    asyncio.run(hub.ingest("beta", "sam", "private:sam", "secret in beta"))
    alpha = store.events("alpha")
    beta = store.events("beta")
    assert alpha[0].visibility == "public"
    assert all(e.text != "secret in beta" for e in alpha)
    assert beta[0].visibility == "private:sam"


def test_plan_like_dm_gets_public_suggestion_without_group_thread():
    store = Store(":memory:")
    linq = FakeLinq()
    hub = RoomHub(store, linq)
    store.bind_chat("dm-sam", "demo", "dm", "sam")
    asyncio.run(hub.ingest("demo", "sam", "private:sam", "I can't do more than $150"))
    linq.sent.clear()
    asyncio.run(hub.ingest("demo", "sam", "private:sam", "let's do the $400 resort"))
    assert linq.sent, "solo DM should still get the cheaper public suggestion"
    assert all(m["chat_id"] == "dm-sam" for m in linq.sent)
    assert all("sam" not in m["text"].lower() for m in linq.sent)
    assert any("How about" in m["text"] or "how about" in m["text"].lower() for m in linq.sent)


def test_group_send_failure_falls_back_to_dms():
    store = Store(":memory:")
    linq = FakeLinq()
    linq.fail_chats.add("grp")
    hub = RoomHub(store, linq)
    store.bind_chat("grp", "demo", "group", None)
    store.bind_chat("dm-sam", "demo", "dm", "sam")
    asyncio.run(hub.ingest("demo", "sam", "private:sam", "I can't do more than $150"))
    linq.sent.clear()
    asyncio.run(hub.ingest("demo", "alex", "public", "let's do the $400 resort"))
    dms = [m for m in linq.sent if m["chat_id"] == "dm-sam" and m.get("ok") is True]
    assert dms, "if Linq rejects the group send, DMs should still get the suggestion"


def test_conflicting_public_plan_posts_anonymous_group_suggestion():
    store = Store(":memory:")
    linq = FakeLinq()
    hub = RoomHub(store, linq)
    store.bind_chat("grp", "demo", "group", None)
    store.bind_chat("dm-sam", "demo", "dm", "sam")
    asyncio.run(hub.ingest("demo", "sam", "private:sam", "I can't do more than $150"))
    linq.sent.clear()
    asyncio.run(hub.ingest("demo", "alex", "public", "let's do the $400 resort"))
    group = [m for m in linq.sent if m["chat_id"] == "grp"]
    dms = [m for m in linq.sent if m["chat_id"] == "dm-sam"]
    assert group, "group thread should get a public suggestion"
    assert not dms, "successful group send must not copy the suggestion to DMs"
    assert all("sam" not in m["text"].lower() for m in group)
    assert any("How about" in m["text"] for m in group)
    assert all("The current public plan may not fit" not in m["text"] for m in linq.sent)


def test_travel_plan_in_group_gets_suggestion():
    store = Store(":memory:")
    linq = FakeLinq()
    hub = RoomHub(store, linq)
    store.bind_chat("grp", "demo", "group", None)
    store.bind_chat("dm-sam", "demo", "dm", "sam")
    asyncio.run(hub.ingest("demo", "sam", "private:sam", "I can't do more than $150"))
    linq.sent.clear()
    asyncio.run(hub.ingest("demo", "alex", "public", "going to Switzerland"))
    group = [m for m in linq.sent if m["chat_id"] == "grp"]
    assert group
    assert any("how about" in m["text"].lower() or "haul" in m["text"].lower() for m in group)
    assert not [m for m in linq.sent if m["chat_id"] == "dm-sam"]
    linq.sent.clear()
    asyncio.run(hub.ingest("demo", "priya", "public", "let's do the $400 resort"))
    follow = [m for m in linq.sent if m["chat_id"] == "grp"]
    assert follow, "a new expensive plan should still get a group reply"


def test_sqlite_file_replay(tmp_path):
    path = tmp_path / "plusone.db"
    store = Store(path)
    store.append_event("demo", 1.0, "sam", "public", "hello table")
    store.close()
    store2 = Store(path)
    events = store2.events("demo")
    assert events[0].text == "hello table"
    store2.close()
