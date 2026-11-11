"""Offline display translations. Never change the raw identifiers written to a mod.

Exact names come from the user's message tables. Identifier explanations use a
small editorial glossary and learned name aliases; unknown text stays visible.
"""
from dataclasses import dataclass
import re
import unicodedata

JAPANESE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]')
PREFIXES = {
    'AID': 'Appearance', 'VID': 'Variation', 'FID': 'Appearance',
    'LID': 'Learning', 'GLID': 'Progression', 'PRF': 'Profile',
    'RID': 'Reference', 'BID': 'Affiliation', 'DID': 'Difficulty',
    'PID': 'Character', 'JID': 'Class', 'SID': 'Skill', 'IID': 'Item',
}
# These are identifier explanations, not claims about undocumented engine behavior.
GLOSSARY = {
    '第一部':'Part 1', '第二部':'Part 2', '第三部':'Part 3', '二部以降':'Part 2 onward',
    '女性':'Female', '男性':'Male', '即位後':'After coronation', '正式':'Formal',
    '５年後':'Five years later', '海王討伐後':'After the Sea King defeat',
    'マント有り':'With cloak', 'マント無し':'Without cloak', 'マント':'Cloak',
    'フード無し':'Without hood', '両腕':'Both arms', 'デフォルト衣装':'Default outfit',
    '盾非表示キャラ':'Hide shield', '拠点':'Base', 'デモ':'Demo', '劇場':'Theater', 'ダンジョン':'Dungeon',
    '共有': 'Shared', '兵種解放': 'Class unlock', '攻勢': 'Offense', '守勢': 'Defense',
    '下馬': 'Dismounted', '篇': 'Route',
    '無し': 'None', '無職': 'No class', '汎用': 'Generic', 'デフォルト': 'Default',
    'モブ': 'Generic unit', '大人': 'Adult', '子供': 'Child', '老人': 'Elder',
    '衣装不定': 'Unspecified outfit', '動物': 'Animal', '軍団兵': 'Legion soldier',
    '本人': 'Identity marker', '主人公用輸送隊': 'Protagonist convoy',
    '主人公': 'Protagonist', '輸送隊': 'Convoy', 'ブレイズ可能': 'Blaze enabled',
    'ブレイズ切替': 'Switch Blaze', 'ブレイズ': 'Blaze', 'オーバーブレイズ許可': 'Overblaze permission',
    '血印持ち': 'Blood-mark bearer', '冥府値': 'Underworld value',
    '冥府の加護': 'Underworld blessing', '内部必殺': 'Internal critical modifier',
    '強敵': 'Strong enemy', '将星': 'Commander', '撃破対象': 'Defeat target',
    '敗北対象': 'Loss-condition target', 'ストック': 'Stock', '固定': 'Fixed',
    '面識参加禁止': 'Disallow acquaintance participation', '引継禁止': 'Disallow carryover',
    '個人スキル上書禁止': 'Disallow personal-skill override', '騎乗禁止': 'Disallow mounting',
    '行動汚染反転': 'Invert action contamination', '行動汚染無効': 'Disable action contamination',
    '汚染無効': 'Disable contamination', '天門値': 'Heaven-gate value', '天門': 'Heaven gate',
    '機構値': 'Mechanism value', 'バースト加算無効': 'Disable burst accumulation',
    'バースト無効': 'Disable burst', 'テルマエ禁止': 'Disallow thermae',
    '連動': 'Linked', '固有アイテム表示': 'Show personal item', '所属前': 'Before joining',
    '開始時': 'At start', '所属': 'Affiliation', '無所属': 'Unaffiliated', '野良': 'Wild',
    'クラン': 'Clan', '幼少時': 'Childhood', '個別設定': 'Individual setting',
    'アガルタ': 'Agartha', '救世主軍': 'Savior army',
    '冥界軍': 'Underworld army', '連合軍': 'Allied army', '神殿': 'Temple',
    'ミトラス修道会': 'Mithras order', 'ダグザ帝国軍': 'Dagda imperial army',
    'サラミス軍': 'Salamis army', 'アラゴ軍': 'Arago army', '盗賊': 'Bandit',
    'コンロンの民': 'People of Kunlun', 'コンロン': 'Kunlun', 'クイックバトル用': 'For quick battle',
    'スキルチェック': 'Skill check', 'チュートリアル': 'Tutorial', 'テスト': 'Test',
    '外套あり': 'With cloak', '外套なし': 'Without cloak', '腰の武器なし': 'No weapon at waist',
    '武器なし': 'No weapon', '眼帯なし': 'Without eyepatch', '弱点': 'Weak point',
    '小型': 'Small', '大型': 'Large', '不明': 'Unknown', '機械': 'Machine',
    '呪詛': 'Curse', '文様': 'Pattern', '第3部': 'Part 3', '3部': 'Part 3', '2部': 'Part 2',
    '強': 'Strong', '敵': 'Enemy', '味方': 'Ally', '男': 'Male', '女': 'Female',
    'クマ肉': 'Bear meat', 'サソリ肉': 'Scorpion meat', 'オオカミ肉': 'Wolf meat',
    'トカゲ肉': 'Lizard meat', '海獣肉': 'Sea-beast meat', '砂虫肉': 'Sandworm meat',
    '巨大肉': 'Giant meat', '虫真珠': 'Insect pearl', 'ルフ肉': 'Roc meat',
    '歩行兵士': 'Foot soldier', '剣盗賊': 'Sword bandit', '斧盗賊': 'Axe bandit',
    '弓盗賊': 'Bow bandit', '炎呪い師': 'Fire caster', '風呪い師': 'Wind caster',
}


# Additional editorial vocabulary for internal skill flags and links. Exact game
# text still takes precedence, and these remain marked as approximate glossary.
GLOSSARY.update({
    '与ダメージ':'Damage dealt','被ダメージ':'Damage taken','ダメージ':'Damage',
    '物理攻撃':'Physical attack','魔法攻撃':'Magic attack','物理防御':'Physical defense','魔法防御':'Magic defense',
    '戦技':'Combat art','猛撃':'Special attack','反撃':'Counterattack','追撃':'Follow-up attack',
    '再行動':'Act again','再移動':'Move again','移動':'Movement','行動':'Action',
    '禁止':'Prohibited','無効':'Disabled','無敵':'Invincible','付与':'Grant','解除':'Remove',
    '発動':'Activate','選択':'Selection','発射':'Launch','命中':'Hit','回避':'Avoid',
    '必殺':'Critical','威力':'Power','射程':'Range','耐久':'Durability','消費':'Cost',
    '回復':'Recovery','習得':'Learn','装備':'Equip','強化':'Upgrade','召喚':'Summon',
    '待機':'Wait','撃破':'Defeat','戦闘':'Combat','発生':'Trigger','追加':'Additional',
    '効果':'Effect','状態':'Status','異常':'Ailment','強制':'Forced','確率':'Chance',
    '有効':'Enabled','対象':'Target','周囲':'Surrounding','範囲':'Area','連撃':'Combo',
})


@dataclass(frozen=True)
class Translation:
    text: str
    source: str


class Translator:
    def __init__(self, names=None, catalog=None, overrides=None):
        self.names = names or {}
        self.catalog = catalog or {}
        self.overrides = overrides or {}
        self.cache = {}
        self.rebuild()

    def rebuild(self):
        self.cache.clear()
        self.words = {unicodedata.normalize('NFKC', k): v for k, v in GLOSSARY.items()}
        candidates = {}
        for key, hint in self.catalog.items():
            name = self.names.get(hint, '').strip()
            tail = key.partition('_')[2]
            if name and tail and JAPANESE.search(tail) and '\n' not in name:
                candidates.setdefault(unicodedata.normalize('NFKC', tail), set()).add(name)
        for tail, names in candidates.items():
            if len(names) == 1:
                self.words[tail] = next(iter(names))
        self.words.update({unicodedata.normalize('NFKC', k): v for k, v in self.overrides.items()})
        self.keys = sorted(self.words, key=len, reverse=True)
        self.by_initial = {}
        for key in self.keys:
            if key:
                self.by_initial.setdefault(key[0], []).append(key)

    def resolve(self, value):
        if value in self.cache:
            return self.cache[value]
        result = self._resolve(value)
        self.cache[value] = result
        return result

    def _resolve(self, value):
        if not value:
            return Translation('—', 'Empty')
        if value in self.overrides:
            return Translation(self.overrides[value], 'Custom')
        name = self.names.get(value) or self.names.get(self.catalog.get(value, ''))
        if name:
            return Translation(name.replace('\n', ' '), 'English text')
        if not JAPANESE.search(value):
            return Translation(value, 'Identifier')
        prefix, sep, tail = value.partition('_')
        tag = PREFIXES.get(prefix) if sep else None
        text = unicodedata.normalize('NFKC', tail if tag else value)
        if text in self.words:
            return Translation((tag + ': ' if tag else '') + self.words[text], 'Glossary')
        pieces = []
        i = 0
        matched = False
        while i < len(text):
            key = next((k for k in self.by_initial.get(text[i], ()) if text.startswith(k, i)), None)
            if key:
                pieces.append(' ' + self.words[key] + ' ')
                i += len(key)
                matched = True
            else:
                pieces.append(text[i])
                i += 1
        if not matched:
            return Translation('No translation yet', 'Untranslated')
        gloss = re.sub(r'\s+', ' ', ''.join(pieces).replace('_', ' / ')).strip()
        return Translation((tag + ': ' if tag else '') + gloss,
                           'Partial glossary' if JAPANESE.search(gloss) else 'Glossary')
