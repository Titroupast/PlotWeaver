from openai import OpenAI
from config import ARK_API_KEY, ARK_MODEL, ARK_BASE_URL
from prompts import SYSTEM_PROMPT, USER_TEMPLATE

def build_client() -> OpenAI:
    return OpenAI(
        api_key=ARK_API_KEY,
        base_url=ARK_BASE_URL,
    )


def generate_chapter(previous_chapter: str, requirements: str) -> str:
    client = build_client()

    user_prompt = USER_TEMPLATE.format(
        previous_chapter=previous_chapter.strip(),
        requirements=requirements.strip(),
    )

    resp = client.chat.completions.create(
        model=ARK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    return resp.choices[0].message.content.strip()


if __name__ == "__main__":
    previous_chapter = """
    林夜站在天台边缘，夜风吹得校服猎猎作响。
    他刚刚确认，妹妹留下的那枚怀表，内部刻着一个陌生名字。
    而那个名字，正是学生会长不该知道的秘密。
    """

    requirements = """
    请续写下一章，要求：
    1. 保持日系轻小说叙事感，偏少年向。
    2. 第三人称有限视角，主要跟随林夜。
    3. 本章要推进“怀表秘密”这条线。
    4. 结尾必须留下明显悬念。
    """

    chapter = generate_chapter(previous_chapter, requirements)
    print(chapter)
