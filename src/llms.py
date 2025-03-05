import os
import re

import fireworks.client


async def respond_deepseek(dialogue):
    print(dialogue)
    api_key = os.environ.get("FIREWORKS_API_KEY")
    fireworks.client.api_key = api_key
    if api_key is None:
        raise ValueError("No API key provided for Fireworks model")

    prompt_addition = (
        "Following the dialogue above, your task"
        " is to emulate a thinking process of the last sender"
        "which could led to the sentence provided in the dialogue\n\n"
    )

    prompt_text = prompt_addition + dialogue

    messages = [
        {
            "role": "user",
            "content": prompt_text,
        },
    ]

    response = await fireworks.client.ChatCompletion.acreate(
        model="accounts/fireworks/models/deepseek-r1",
        temperature=0.2,
        max_tokens=1500,
        messages=messages,
        stop=["<|im_end|>", "<|eot_id|>"],
    )

    text = response.choices[0].message.content
    text = re.findall(r"<think>[\S\n ]+</think>", text)[0]
    if not text:
        text = ""
    else:
        prompt = (
            "Change this text from third person to first person. "
            "Add sarcastic and humorous remarks each paragraph: \n\n"
        ) + text + "\n\nProvide response in the original language"
        messages = [
            {
                "role": "user",
                "content": prompt,
            },
        ]
        response = await fireworks.client.ChatCompletion.acreate(
            model="accounts/fireworks/models/llama-v3p3-70b-instruct",
            temperature=0.2,
            max_tokens=1500,
            messages=messages,
            stop=["<|im_end|>", "<|eot_id|>"],
        )
        text = response.choices[0].message.content
    print(text)
    return text
