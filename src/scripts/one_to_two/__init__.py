import builtins
import json
import os
import time
import typing as t

import mariadb

from adapting import interaction
from adapting.interaction import _get_or_create_the_one_piece
from dc_utils import connect
from dc_utils.rank import CommunityRank, JumpediaRank
from structures import db
from structures.attribute import AnyAttributeT, TaskAttribute, UserAttribute
from structures.community import CommunityLimits
from structures.list import Kind, List
from structures.task import Task
from utils import numbers, orm, secret, text
from utils.text import NormStr, RealStr

DATA_PATH = os.path.join(os.path.abspath(__file__.removesuffix("__init__.py")), "data")

JUMP_DATA_PATH = os.path.join(DATA_PATH, "jump_data.json")
USER_JUMPS = os.path.join(DATA_PATH, "user_jumps")


def create_attributes(
    c: orm.Cursor, list: List, unproven: bool
) -> dict[str, AnyAttributeT]:
    old_to_new: dict[str, AnyAttributeT] = {
        "name": list.get_static_attribute_by_kind(c, Kind.NAME)
    }

    diff_collection: builtins.list[tuple[RealStr, t.Iterable[RealStr]]] = []

    for diff in [
        "0/10",
        "0.5/10",
        "1/10",
        "1.5/10",
        "2/10",
        "2.5/10",
        "3/10",
        "3.5/10",
        "4/10",
        "4.5/10",
        "5/10",
        "5.5/10",
        "6/10",
        "6.5/10",
        "7/10",
        "7.5/10",
        "8/10",
        "8.5/10",
        "9/10",
        "9.5/10",
        "10/10",
        "Low Elite",
        "Mid Elite",
        "High Elite",
        "Insanity Elite",
        "God Tier",
        "Hell Tier",
    ]:
        aliases: builtins.list[str] = []
        n, non_elite, _ = diff.partition("/")

        if non_elite:
            aliases.append(n)

            if n == "0.5":
                aliases.append(".5")
                aliases.append(".5/10")

            for syn in (diff, *aliases):
                if "." in syn:
                    aliases.append(syn.replace(".", ","))
        else:
            aliases.append(diff.partition(" ")[0])

            if diff == "Insanity Elite":
                aliases.append("Ins")

        diff_collection.append((RealStr(diff), map(RealStr, aliases)))

    if not unproven:
        old_to_new["diff"] = list.create_attribute(
            c,
            TaskAttribute,
            RealStr("Difficulty"),
            map(RealStr, ["Diff", "Dif", "D", "Difficult"]),
            str,
            1,
            collection=diff_collection,
        )

    del diff_collection

    old_to_new["type"] = list.create_attribute(
        c,
        TaskAttribute,
        RealStr("Type"),
        map(RealStr, ["T", "Ty"]),
        str,
        32,
    )

    loc_collection: builtins.list[tuple[RealStr, t.Iterable[RealStr]]] = []

    for loc in [
        "Mushroom Kingdom",
        "Cap Kingdom",
        "Cascade Kingdom",
        "Sand Kingdom",
        "Lake Kingdom",
        "Wooded Kingdom",
        "Cloud Kingdom",
        "Lost Kingdom",
        "Metro Kingdom",
        "Snow Kingdom",
        "Seaside Kingdom",
        "Luncheon Kingdom",
        "Ruined Kingdom",
        "Bowser's Kingdom",
        "Moon Kingdom",
        "Dark Side",
        "Darker Side",
        "Odyssey",
    ]:
        aliases: builtins.list[str] = []

        kingdom, space_exists, _ = loc.partition(" ")

        if space_exists:
            aliases.append(kingdom)

        if kingdom.startswith("Bowser"):
            for syn in (loc, *aliases):
                aliases.append(syn.replace("'s", "s"))
                aliases.append(syn.replace("'s", ""))

        loc_collection.append((RealStr(loc), map(RealStr, aliases)))

    old_to_new["location"] = list.create_attribute(
        c,
        TaskAttribute,
        RealStr("Location"),
        map(RealStr, ["L", "Loc", "Kingdom", "K"]),
        str,
        2,
        collection=loc_collection,
    )

    del loc_collection

    ftp_to_aliases: dict[str, builtins.list[str]] = {
        "Finder": ["F", "Find", "Found", "Founder"],
        "Taser": ["TAS", "TASed"],
        "Prover": ["P", "Prove", "Profer"],
    }

    for ftp in ["Finder", "Taser", "Prover"]:
        old_to_new[ftp.lower()] = list.create_attribute(
            c,
            TaskAttribute,
            RealStr(ftp),
            map(RealStr, ftp_to_aliases[ftp]),
            str,
            32,
        )

    old_to_new["server"] = list.create_attribute(
        c,
        TaskAttribute,
        RealStr("Server"),
        map(RealStr, ["S"]),
        str,
        1,
        collection=tuple(
            (RealStr(k), map(RealStr, v))
            for k, v in {
                "SMO Trickjumping Server": [
                    "Main",
                    "Main Server",
                    "SMO Trickjumping",
                    "SMO Trickjump",
                    "Main Trickjumping Server",
                    "Main Trickjump Server",
                ],
                "Database": ["The Trickjump Database", "Database Server", "DB"],
            }.items()
        ),
    )

    old_to_new["links"] = list.create_attribute(
        c, TaskAttribute, RealStr("Link"), map(RealStr, ["Links"]), str, 32
    )

    old_to_new["extra"] = list.create_attribute(
        c,
        TaskAttribute,
        RealStr("Description"),
        map(RealStr, ["I", "Info", "Desc", "Information", "Extra", "E"]),
        str,
        32,
    )

    if not unproven:
        old_to_new["proof"] = list.create_attribute(
            c, UserAttribute, RealStr("Proof"), (), str, 1
        )

    return old_to_new


def _split_up(v: list[str], c: str) -> list[str]:
    new_v: builtins.list[str] = []

    for slot in v:
        if len(slot) < 256:
            new_v.append(slot)
            continue

        parts = slot.split(c)
        new_parts: builtins.list[str] = []

        for i, part in enumerate(parts):
            part = part.strip()

            if not part:
                continue

            # Not last
            if i < len(parts) - 1:
                part = part + c

            new_parts.append(part)

        new_v.extend(new_parts)

    return new_v


def create_tasks(
    c: orm.Cursor,
    list: List,
    old_to_new_attributes: dict[str, AnyAttributeT],
    unproven: bool,
) -> list[Task]:
    with open(JUMP_DATA_PATH) as f:
        jump_data: dict[str, dict[str, str | builtins.list[str]]] = json.load(f)

    tasks: builtins.list[Task] = []

    for i, jump in enumerate(jump_data.values(), start=1):
        tavm: dict[int, t.Sequence[RealStr]] = {}

        name: RealStr | None = None

        if unproven != (jump["diff"] == "Unproven"):
            continue

        for old_attr_name, v in jump.items():
            if old_attr_name == "tier":
                continue

            if old_attr_name == "name":
                name = RealStr(v)  # type: ignore
                continue

            if unproven and old_attr_name == "diff":
                continue

            attr = old_to_new_attributes[old_attr_name]

            if isinstance(v, str):
                v = [v]

            for char in ".!":
                v = _split_up(v, char)

            tavm[attr.id] = tuple(map(RealStr, v))

        assert name

        tasks.append(list.create_task(c, name, (), tavm))

        if i % 10 == 0:
            print(f"{i}/{len(jump_data)} tasks inserted!")

        if i % 100 == 0:
            c.commit()

    return tasks


def give_jumps_to_users(
    c: orm.Cursor, list: List, proof_attr: UserAttribute, tasks: dict[NormStr, Task]
) -> None:
    all_file_names = os.listdir(USER_JUMPS)

    for i, file_name in enumerate(all_file_names, start=1):
        file_path = os.path.join(USER_JUMPS, file_name)

        if file_path.endswith("backup.json"):
            continue

        user_id: int = int(file_name.removesuffix(".json"))

        community_user = list.community.get_or_create_community_user(
            c,
            list.community.jumpedia.get_or_create_jumpedia_user(
                c, user_id, str(user_id), JumpediaRank.DEFAULT, False, False
            ),
            CommunityRank.DEFAULT,
            list.id,
            False,
            True,
        )

        with open(file_path) as f:
            user_jump_data: dict[str, dict[str, str]] = json.load(f)

        print(
            f"Giving jumps to: {user_id} ({len(user_jump_data)}) ({i}/{len(all_file_names)})"
        )

        for i, (jump_name, data) in enumerate(user_jump_data.items(), 1):
            task = tasks.get(text.NormStr(jump_name), None)

            if task is None:
                continue

            proof = data.get("proof", None)

            list.give_task_to_community_user(
                c,
                task.id,
                community_user.id,
                {proof_attr.id: [RealStr(proof)]} if proof else {},
            )

            if i % 10 == 0:
                print(f"{i}/{len(user_jump_data)} jumps given to user!")

            if i % 100 == 0:
                c.commit()


def main():
    input("WARNING!!!!!!! DATABASE WILL BE WIPED!!!! ARE YOU SURE???????")
    input("VERY SURE??")

    input("FINAL QUESTION: ARE U SURE??????")

    print("ok...")

    time.sleep(0.5)

    # while True:
    #     input("Locked rn!")

    if input("If you are 100% sure (NO GOING BACK) then enter 'yes': ") != "yes":
        print("Aborted!")
        exit()

    META_C = orm.Cursor(
        conn := mariadb.connect(
            **secret.listen().DATABASE_CONNECTION_DATA
            | {"db": None}
            | {"user": "root", "password": input("Please enter password for root: ")}
        ),
        conn.cursor(dictionary=True),
    )

    META_C.raw_execute("DROP DATABASE IF EXISTS jumpedia")
    META_C.commit()

    META_C._close_connection()

    THE_ONE_PIECE = interaction._get_or_create_the_one_piece()

    C = connect.get_new_connection_cursor_adapter()

    community = THE_ONE_PIECE.create_community(
        C,
        RealStr("SMO Trickjumping"),
        469869605570084886,
        THE_ONE_PIECE.get_or_create_jumpedia_user(
            C, 679564566769827841, "JoniKauf", JumpediaRank.JONIKAUF, True, True
        ),
        {
            "community_list_count_max": 32,
            "list_attribute_count_max": 32,
            "list_task_count_max": numbers.INT32_MAX,
            "attribute_alias_count_max": 32,
            "attribute_task_value_slot_count_max": 32,
            "attribute_collection_entry_count_max": 1024,
            "attribute_collection_entry_alias_count_max": 32,
        },
    )

    main_list = community.create_list(C, RealStr("Main"))

    community.set_default_selected_list(C, main_list.id)

    unproven_list = community.create_list(C, RealStr("Unproven"))

    print("Creating attributes...")
    OLD_TO_NEW_ATTRS = create_attributes(C, main_list, False)
    OLD_TO_NEW_ATTRS_UNPROVEN = create_attributes(C, unproven_list, True)
    print("Created attributes!")

    print("Creating tasks...")
    TASKS = create_tasks(C, main_list, OLD_TO_NEW_ATTRS, False)
    _ = create_tasks(C, unproven_list, OLD_TO_NEW_ATTRS_UNPROVEN, True)
    print("Created tasks!")

    proof_attr: UserAttribute = OLD_TO_NEW_ATTRS["proof"]  # type: ignore

    # main_list = _JUMPEDIA.get_community_by_name(
    #     NormStr("SMO Trickjumping")
    # ).get_list_by_name(NormStr("Main"))

    # assert main_list is not None

    # proof_attr = tuple(
    #     main_list.get_attributes_by_name(UserAttribute, NormStr("proof")).values()
    # )[0]
    # TASKS = main_list.get_tasks()

    print("Giving users tasks...")
    give_jumps_to_users(
        C, main_list, proof_attr, {task.norm_name: task for task in TASKS}
    )
    print("Gave users tasks!")

    C.commit()

    # print("Giving users tasks...")
    # give_jumps_to_users(
    #     main_list, OLD_TO_NEW_ATTRS["proof"], {task.norm_name: task for task in TASKS}
    # )
    # print("Gave users tasks!")


# if __name__ == "__main__":
main()

exit()
