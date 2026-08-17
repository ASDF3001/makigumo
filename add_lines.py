import os

new_lines = {
    "aege.txt": [
        "「あぁっ…んっ、はぁっ…！ もっと、ですか…？♡」",
        "「…っ！ ひゃああっ…！ ダメ、そこは…っ！」"
    ],
    "batou.txt": [
        "「ほんっとうに救いようのないド変態ですね。生きてて恥ずかしくないんですか？」",
        "「キモいです。私の視界に入らないでくれませんか？」"
    ],
    "kanbyou.txt": [
        "「んっ…おでこ、熱いですね。今日は私がずーっと看病してあげますからね。」",
        "「ほら、お薬の時間ですよ。口移しで…なんて、冗談ですからね！」"
    ],
    "soine.txt": [
        "「んっ…あったかいですね…。{user}さんの鼓動、聞こえます…♡」",
        "「今日はもう、このまま離してあげませんからね…？」"
    ],
    "ohayo.txt": [
        "「んぁ…おはよ、ございます…。あと5分だけ、一緒に寝ましょうよぉ…」"
    ],
    "oyasumi.txt": [
        "「おやすみなさい。…寝顔、こっそり見させてもらいますね？♡」"
    ],
    "kawaii.txt": [
        "「っ…！ そ、そんな事言っても、何も出ませんからね！」"
    ],
    "nuita.txt": [
        "「またですか！？ 少しは自重という言葉を覚えてください！」"
    ],
    "mimiuchi.txt": [
        "「（こしょこしょ…）…ふふっ、耳、赤くなってますよ？♡」"
    ],
    "oshioki.txt": [
        "「ほら、そこ。動かないでくださいね？ たっぷりお仕置きしてあげますから…♡」"
    ],
    "shitto.txt": [
        "「…さっきから他の子の話ばっかりですね。私のこと、もうどうでもいいんですか…？」"
    ]
}

for filename, lines in new_lines.items():
    filepath = os.path.join("lines", filename)
    if os.path.exists(filepath):
        with open(filepath, "a", encoding="utf-8") as f:
            for line in lines:
                f.write("\n" + line)

print("Added lines to text files.")
