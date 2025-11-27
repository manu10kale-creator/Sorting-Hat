import streamlit as st
from dotenv import load_dotenv
import os
from openai import OpenAI
import io
from PIL import Image, ImageDraw, ImageFont
import string
from collections import defaultdict

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("OPENAI_API_KEY missing. Add it to .env.")
    st.stop()
else:
    client = OpenAI(api_key=api_key)

def build_prompt(name, q1, q2, q3, q4, q5):
    with open("prompt.txt", "r", encoding="utf-8") as f:
        template = f.read()


    data = {
        "name": name or "",
        "q1": q1 or "",
        "q2": q2 or "",
        "q3": q3 or "",
        "q4": q4 or "",
        "q5": q5 or ""
    }


    class SafeDict(defaultdict):
        def __missing__(self, key):
            return ""

    safe_map = SafeDict(str, data)
    # Use format_map which won't raise KeyError because SafeDict returns "" for missing keys
    filled = template.format_map(safe_map)
    return filled

def generate_sorting(name, q1, q2, q3, q4, q5):
    full_prompt = build_prompt(name, q1, q2, q3, q4, q5)

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": full_prompt}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content

st.set_page_config(page_title="Sorting Hat 🎩",page_icon="🎩", layout="centered")
st.title("🎩 The Sorting Hat Awaits!")
st.markdown("""
Welcome, young witch or wizard.  
Answer a few questions, and I shall reveal your truu Hogwarts House...
""")
st.markdown("---")
st.write("The questions will appear here soon..")
name = st.text_input("Your name:")

q1 = st.radio(
    "In a dangerous situation, you...",
    (
        "Charge in without hesitation",
        "Calmly make a plan",
        "Look for a clever workaround",
        "Protect the vulnerable first",
    ),
)

q2 = st.radio(
    "You value most:",
    ("Courage", "Ambition", "Knowledge", "Loyalty"),
)

q3 = st.radio(
    "In a team, you are usually the:",
    ("Bold leader", "Strategic planner", "Idea person / problem solver", "Reliable supporter"),
)

q4 = st.radio(
    "Which describes you best?",
    (
        "I act on impulse for what's right",
        "I aim to get ahead and lead",
        "I think before I act and love puzzles",
        "I’m steady, fair, and patient",
    ),
)

q5 = st.text_area("Anything else the Sorting Hat should know? (optional)", max_chars=200)

st.markdown("")



# --- helper: map house to emoji + color ---
HOUSE_STYLE = {
    "gryffindor": {"emoji": "🦁", "color": (165, 28, 28)},    # dark red
    "slytherin": {"emoji": "🐍", "color": (6, 102, 59)},      # dark green
    "ravenclaw": {"emoji": "🦅", "color": (25, 42, 86)},      # navy
    "hufflepuff": {"emoji": "🦡", "color": (210, 170, 30)},   # gold
}

def normalize_house(house_name):
    if not house_name:
        return None
    h = house_name.strip().lower()
    # map common outputs to canonical names
    if "gryff" in h:
        return "gryffindor"
    if "slyth" in h:
        return "slytherin"
    if "raven" in h:
        return "ravenclaw"
    if "huffle" in h:
        return "hufflepuff"
    # fallback: pick first word
    return h.split()[0]

def make_house_card_png(name, house, hat_line, explanation):
    # Card size
    W, H = 800, 500

    # Normalize house key
    house_key = normalize_house(house) or "gryffindor"
    style = HOUSE_STYLE.get(house_key, HOUSE_STYLE["gryffindor"])
    bg = style["color"]
    emoji = style["emoji"]

    # Create blank image
    img = Image.new("RGB", (W, H), color=bg)
    draw = ImageDraw.Draw(img)

    # Fonts (fallback to default)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        subtitle_font = ImageFont.truetype("DejaVuSans.ttf", 30)
        text_font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except:
        title_font = subtitle_font = text_font = ImageFont.load_default()

    # HOUSE BANNER (top)
    banner_h = 110
    draw.rectangle([(0, 0), (W, banner_h)], fill=(0, 0, 0, 180))
    draw.text((30, 25), f"{emoji} {house.title()}", font=title_font, fill=(255, 215, 0))

    # NAME
    name_to_show = name if name else "A Hogwarts Student"
    draw.text((30, banner_h + 20), f"Name: {name_to_show}", font=subtitle_font, fill=(255, 255, 255))

    # WRAPPED HAT LINE PARAGRAPH
    def wrap(text, font, max_w):
        words = text.split()
        lines, current = [], ""
        for w in words:
            test = (current + " " + w).strip()
            if draw.textlength(test, font) <= max_w:
                current = test
            else:
                lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines

    wrapped_hat = wrap(hat_line, text_font, W - 60)

    y_pos = banner_h + 90
    for line in wrapped_hat:
        draw.text((30, y_pos), line, font=text_font, fill=(255, 255, 255))
        y_pos += 32

    # FOOTER EXPLANATION BAR
    footer_h = 90
    draw.rectangle([(0, H - footer_h), (W, H)], fill=(0, 0, 0))

    # Trim explanation text
    short_expl = explanation[:180] + ("..." if len(explanation) > 180 else "")
    expl_lines = wrap(short_expl, text_font, W - 60)

    y_footer = H - footer_h + 15
    for line in expl_lines:
        draw.text((30, y_footer), line, font=text_font, fill=(200, 200, 200))
        y_footer += 25

    # Save image to bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

# --- Main button behaviour: replace your old if block with this ---
if st.button("🎩 Sort Me!"):
    if not (q1 and q2 and q3 and q4):
        st.warning("Please answer the main questions so the Sorting Hat can make its choice.")
    else:
        with st.spinner("The Sorting Hat is thinking..."):
            # Get raw model output (the prompt requires structured sections)
            raw_output = generate_sorting(name or "Mysterious One", q1, q2, q3, q4, q5)

        # Try to extract House line by naive search (we rely on prompt's "## 🪄 House" header)
        # We'll display the full raw_output using markdown to keep structure.
        st.markdown("---")

        # attempt to parse house name from the response for styling
        house_line = None
        for line in raw_output.splitlines():
            if line.strip().lower().startswith("**") and "{" not in line:
                # sometimes bold house lines come as **House**
                house_line = line.strip().strip("*").strip()
                break
            if line.strip().lower().startswith("## 🪄 house"):
                # next non-empty line is house
                idx = raw_output.splitlines().index(line)
                if idx + 1 < len(raw_output.splitlines()):
                    house_line = raw_output.splitlines()[idx+1].strip().strip("*").strip()
                    break
            # fallback: look for a single known house word
            for candidate in ["Gryffindor", "Slytherin", "Ravenclaw", "Hufflepuff"]:
                if candidate.lower() in line.lower():
                    house_line = candidate
                    break
            if house_line:
                break

        house_key = normalize_house(house_line) or None
        style = HOUSE_STYLE.get(house_key, {"emoji":"🎩","color":(80,80,80)})
        color = style["color"]
        emoji = style["emoji"]

        # header with color
        st.markdown(f"<h1 style='color: rgb{color};'>{emoji} {house_line or 'House Unknown'}</h1>", unsafe_allow_html=True)

        # show the cinematic output (the prompt already formats sections)
        st.markdown(raw_output)

        # show confetti / balloons
        try:
            st.balloons()
        except Exception:
            pass

        # generate a house card PNG and provide download
        # try to extract Hat line and explanation for card; naive parse:
        hat_line = ""
        explanation = ""
        lines = raw_output.splitlines()
        for i, ln in enumerate(lines):
            l = ln.strip()
            if l.lower().startswith("## 🎩 sorting hat's words"):
                if i+1 < len(lines):
                    hat_line = lines[i+1].strip()
            if l.lower().startswith("## 📜 why i chose this for you"):
                # grab following 2 lines as explanation
                explanation = " ".join([lines[i+1].strip() if i+1 < len(lines) else "",
                                        lines[i+2].strip() if i+2 < len(lines) else ""]).strip()
        # build PNG bytes
        card_bytes = make_house_card_png(name or "", house_line or "Unknown", hat_line, explanation)

        st.download_button(
            label="📥 Download House Card (PNG)",
            data=card_bytes,
            file_name=f"{(name or 'sorted')}_{(house_line or 'house')}.png",
            mime="image/png"
        )

        st.markdown("---")

