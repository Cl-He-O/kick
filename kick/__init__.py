from mcdreforged.api.all import *
from kick.config import Config

from os import path

from time import monotonic_ns
from threading import Timer, Lock

from typing import Dict

import json

config: Config
CONFIG_PATH = "config/kick.json"

kickList: Dict[str, int]
kickListL = Lock()

Pref = "!!kick"

nanosecond = 1e-9


def time_tr(seconds: int) -> RTextMCDRTranslation:
    minutes = seconds // 60
    hours = minutes // 60

    return tr("time", hours, minutes % 60, seconds % 60)


def kickList_save():
    global kickListL
    with kickListL:
        json.dump(kickList, open(config.cache_file, "w"))


def tr(translation_key: str, *args) -> RTextMCDRTranslation:
    return ServerInterface.get_instance().rtr("kick.{}".format(translation_key), *args)


def on_load(server: PluginServerInterface, old):
    global config, kickList
    config = server.load_config_simple(
        CONFIG_PATH, target_class=Config, in_data_folder=False
    )

    try:
        kickList = json.load(open(config.cache_file, "r"))
    except:
        kickList = {}
        kickList_save()

    unkick_startup()
    kickList_save()

    def permission_node(node: AbstractNode):
        return node.requires(
            lambda src: src.has_permission(config.min_permission)
        ).on_error(
            RequirementNotMet,
            lambda src: src.reply(tr("permission.denied")),
            handled=True,
        )

    server.register_command(
        Literal(Pref)
        .runs(on_help)
        .then(
            permission_node(
                QuotableText("target")
                .runs(lambda src, ctx: on_kick(src, ctx["target"], config.minutes))
                .then(
                    Float("minutes").runs(
                        lambda src, ctx: on_kick(src, ctx["target"], ctx["minutes"])
                    )
                )
            )
        )
    )

    server.register_command(Literal(Pref + "-list").runs(on_list))


@new_thread("kick-help")
def on_help(src: CommandSource):
    src.reply(tr("help"))


@new_thread("kick-kick")
def on_kick(src: CommandSource, target: str, t_min: float):
    kick(src.get_server(), target, t_min * 60 / nanosecond)
    kickList_save()
    src.reply(tr("done"))


@new_thread("kick-list")
def on_list(src: CommandSource):
    global kickList, kickListL

    now = monotonic_ns()

    msg = [tr("list.header")]

    with kickListL:
        for player, t in kickList.items():
            dt = (t - now) * nanosecond

            msg.append(tr("list.line", player, time_tr(dt).to_plain_text()))

    src.reply(RTextList(msg))


def unkick_startup():
    server = ServerInterface.get_instance()
    for player, t in kickList.items():
        if t < monotonic_ns():
            Timer((monotonic_ns() - t) * nanosecond, unkick, player)
        else:
            unkick(player)


def kick(server: ServerInterface, target: str, t_ns: int):
    global kickList, kickListL

    with kickListL:
        kickList[target] = monotonic_ns() + t_ns

        server.execute("whitelist remove {}".format(target))
        server.execute("kick {}".format(target))


def unkick(server: ServerInterface, target: str):
    global kickList, kickListL

    with kickListL:
        server.execute("whitelist add {}".format(target))

        kickList.pop(target)
