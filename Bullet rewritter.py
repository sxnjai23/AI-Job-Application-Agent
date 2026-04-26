
import os
from groq import Groq

# ── Your base resume bullets (edit these to match your actual resume) ──────────
BASE_BULLETS = [
    "Developed a CNN classifier trained on 10,000+ images achieving 91% test accuracy via augmentation and batch normalization.",
    "Built an LLM-powered automation tool that scrapes job descriptions and runs a semantic matching pipeline.",
    "Engineered an RUL prediction system on NASA Turbofan dataset using time-series lag features — reduced RMSE by 12%.",
    "Trained KNN, K-Means, and Decision Tree classifiers on datasets of 1K–50K rows; EDA improved accuracy by 10–15%.",
    "Developed a Linear Regression RUL model on 26K+ sensor readings achieving 85% prediction accuracy.",
    "Built an interactive Streamlit dashboard with CSV upload, real-time predictions, and degradation curve visualization.",
    "Delivered Python-based analytical reports enabling non-technical stakeholders to make data-informed decisions.",
    "Proficient in NLP, CNNs, LSTMs, LangChain, FastAPI, and model deployment using Streamlit.",
]
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY", "Your_API_Key_Here")
)


def rewrite_bullets(job_description: str, bullets: list[str]) -> dict:
    """
    Takes a job description and your resume bullets.
    Returns tailored bullets + extracted keywords.
    """

    bullets_text = "\n".join(f"- {b}" for b in bullets)

    prompt = f"""You are a professional resume optimization expert.

I will give you:
1. A job description
2. My current resume bullet points

Your task:
- Rewrite each bullet point to match the job description keywords and requirements
- Keep the core truth of each bullet — do NOT invent new skills or fake experience
- Use strong action verbs: Developed, Engineered, Built, Optimized, Automated
- Each rewritten bullet must be ONE line only
- Naturally include relevant keywords from the job description
- Keep it credible and realistic — no overclaims

Also extract the top 10 ATS keywords from the job description.

---
JOB DESCRIPTION:
{job_description}

---
MY CURRENT BULLETS:
{bullets_text}

---
Respond in this exact format:

KEYWORDS:
1. keyword one
2. keyword two
(list 10 keywords)

REWRITTEN BULLETS:
- rewritten bullet 1
- rewritten bullet 2
(one bullet per line, same count as input)
"""

    response = client.chat.completions.create(
        model="llama3-8b-8192",   # Free, fast, good quality
        messages=[
            {
                "role": "system",
                "content": "You are an expert ATS resume optimizer. Be concise, accurate, and professional."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.4,          # Low = more consistent output
        max_tokens=1500,
    )

    raw = response.choices[0].message.content

    # Parse the response 
    keywords = []
    rewritten = []

    lines = raw.strip().split("\n")
    mode = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("KEYWORDS"):
            mode = "keywords"
            continue
        if line.upper().startswith("REWRITTEN BULLETS"):
            mode = "bullets"
            continue
        if mode == "keywords" and line[0].isdigit():
            # Remove "1. " prefix
            kw = line.split(".", 1)[-1].strip()
            keywords.append(kw)
        if mode == "bullets" and line.startswith("-"):
            bullet = line.lstrip("- ").strip()
            rewritten.append(bullet)

    return {
        "keywords": keywords,
        "rewritten_bullets": rewritten,
        "raw_response": raw,
        "model_used": response.model,
        "tokens_used": response.usage.total_tokens,
    }


def display_results(result: dict, original_bullets: list[str]) -> None:
    """Pretty print the results."""

    print("\n" + "=" * 60)
    print("TOP ATS KEYWORDS FROM JOB DESCRIPTION")
    print("=" * 60)
    for i, kw in enumerate(result["keywords"], 1):
        print(f"  {i:2}. {kw}")

    print("\n" + "=" * 60)
    print("REWRITTEN BULLETS")
    print("=" * 60)

    rewritten = result["rewritten_bullets"]
    for i, (orig, new) in enumerate(zip(original_bullets, rewritten), 1):
        print(f"\n[{i}] ORIGINAL:")
        print(f"    {orig}")
        print(f"    REWRITTEN:")
        print(f"    {new}")

    print("\n" + "=" * 60)
    print(f"Model  : {result['model_used']}")
    print(f"Tokens : {result['tokens_used']} (Free tier: 6000/min, 500K/day)")
    print("=" * 60)


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("=" * 60)
    print("RESUME BULLET REWRITER — Powered by Groq + LLaMA 3")
    print("=" * 60)

    print("\nPaste the job description below.")
    print("When done, type END on a new line and press Enter:\n")

    jd_lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        jd_lines.append(line)

    job_description = "\n".join(jd_lines)

    if len(job_description.strip()) < 50:
        print("Job description too short. Please paste the full JD.")
        exit(1)

    print("\nRewriting your bullets using Groq API...")

    result = rewrite_bullets(job_description, BASE_BULLETS)
    display_results(result, BASE_BULLETS)

    # Save to file
    output_path = "tailored_bullets.txt"
    with open(output_path, "w") as f:
        f.write("TOP ATS KEYWORDS\n")
        f.write("=" * 40 + "\n")
        for kw in result["keywords"]:
            f.write(f"- {kw}\n")
        f.write("\nREWRITTEN BULLETS\n")
        f.write("=" * 40 + "\n")
        for b in result["rewritten_bullets"]:
            f.write(f"- {b}\n")

    print(f"\nSaved to: {output_path}")