
import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import time
import io

st.set_page_config(
    page_title="SmartSplit Bill AI",
    page_icon="🧾",
    layout="wide"
)

GEMINI_API_KEY = "AQ.Ab8RN6LwldDWyzpAI0RTPB6nZkRnORzFLzAXO1IJ3QlX0K7G4g"
genai.configure(api_key=GEMINI_API_KEY)

def extract_bill(image):
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = """
    Kamu adalah sistem OCR untuk struk belanja Indonesia.
    Ekstrak semua data dari struk ini dan kembalikan dalam format JSON berikut:

    {
      "nama_toko": "...",
      "items": [
        {
          "nama_item": "...",
          "jumlah": 1,
          "harga_per_item": 10000,
          "total_harga_item": 10000
        }
      ],
      "subtotal": 0,
      "biaya_tambahan": [],
      "total": 0
    }

    Aturan penting:
    - Semua harga dalam angka integer TANPA titik/koma (Rp 36.000 -> 36000)
    - Jika tertulis 1 lusin artinya jumlah = 12
    - Jika tidak ada pajak, biaya_tambahan = []
    - Kembalikan HANYA JSON, tanpa teks lain
    """

    response = model.generate_content([prompt, image])
    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except:
        return None

def format_rupiah(angka):
    try:
        return f"Rp {int(angka):,}".replace(",", ".")
    except:
        return "Rp 0"

if "bill_data" not in st.session_state:
    st.session_state.bill_data = None
if "participants" not in st.session_state:
    st.session_state.participants = []
if "assignments" not in st.session_state:
    st.session_state.assignments = {}

st.title("🧾 SmartSplit Bill AI")
st.caption("Upload struk belanja, AI baca otomatis, lalu split tagihan ke tiap orang!")
st.divider()


st.subheader("Step 1 — Upload Struk")
uploaded_file = st.file_uploader("Upload foto struk", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(image, caption="Foto Struk", use_column_width=True)

    with col2:
        st.write("")
        st.write("")
        if st.button("🤖 Scan dengan AI", use_container_width=True, type="primary"):
            with st.spinner("AI sedang membaca struk..."):
                start = time.time()
                result = extract_bill(image)
                elapsed = time.time() - start

            if result:
                st.session_state.bill_data = result
                st.session_state.assignments = {}
                st.success(f"Berhasil! Waktu scan: {elapsed:.2f} detik")
            else:
                st.error("Gagal membaca struk. Coba foto yang lebih jelas.")

st.divider()

if st.session_state.bill_data:
    data = st.session_state.bill_data

    st.subheader("Step 2 — Hasil Bacaan AI")

    nama_toko = data.get("nama_toko", "")
    if nama_toko:
        st.markdown(f"🏪 **{nama_toko}**")

    st.markdown("**Daftar Item:**")
    col_h1, col_h2, col_h3, col_h4 = st.columns([3, 1, 2, 2])
    col_h1.markdown("**Nama Item**")
    col_h2.markdown("**Qty**")
    col_h3.markdown("**Harga Satuan**")
    col_h4.markdown("**Total**")
    st.markdown("---")

    for item in data.get("items", []):
        c1, c2, c3, c4 = st.columns([3, 1, 2, 2])
        c1.write(item.get("nama_item", "-"))
        c2.write(str(item.get("jumlah", 1)))
        c3.write(format_rupiah(item.get("harga_per_item", 0)))
        c4.write(format_rupiah(item.get("total_harga_item", 0)))

    st.markdown("---")
    st.metric("Subtotal", format_rupiah(data.get("subtotal", 0)))

    for bt in data.get("biaya_tambahan", []):
        st.metric(bt.get("nama", "Biaya Tambahan"), format_rupiah(bt.get("nilai", 0)))

    st.metric("TOTAL BILL", format_rupiah(data.get("total", 0)))
    st.divider()


    st.subheader("Step 3 — Masukkan Nama Peserta")

    col_input, col_btn = st.columns([3, 1])
    new_name = col_input.text_input("Nama", label_visibility="collapsed", placeholder="Contoh: Budi")
    if col_btn.button("➕ Tambah", use_container_width=True):
        if new_name and new_name not in st.session_state.participants:
            st.session_state.participants.append(new_name)
            st.rerun()

    if st.session_state.participants:
        cols_p = st.columns(len(st.session_state.participants))
        for idx, p in enumerate(st.session_state.participants):
            cols_p[idx].markdown(f"👤 **{p}**")

        if st.button("🗑️ Reset Peserta"):
            st.session_state.participants = []
            st.session_state.assignments = {}
            st.rerun()

    st.divider()

  
    if st.session_state.participants:
        st.subheader("Step 4 — Siapa Bayar Tiap Item?")

        items = data.get("items", [])
        for i, item in enumerate(items):
            c1, c2 = st.columns([3, 2])
            c1.write(f"**{item.get('nama_item', '-')}** — {format_rupiah(item.get('total_harga_item', 0))}")
            selected = c2.selectbox(
                "Dibayar oleh",
                options=st.session_state.participants,
                key=f"assign_{i}",
                label_visibility="collapsed"
            )
            st.session_state.assignments[i] = selected

        st.divider()

        st.subheader("Step 5 — Rincian Tagihan Per Orang")

        total_bill = data.get("total", 0)
        subtotal = data.get("subtotal", 0) or 1
        total_biaya_tambahan = sum(
            bt.get("nilai", 0) for bt in data.get("biaya_tambahan", [])
        )

        tagihan = {p: 0 for p in st.session_state.participants}
        for i, item in enumerate(items):
            who = st.session_state.assignments.get(i, st.session_state.participants[0])
            item_total = item.get("total_harga_item", 0)
            proporsi = item_total / subtotal if subtotal > 0 else 0
            tagihan[who] += item_total + (proporsi * total_biaya_tambahan)

        cols_t = st.columns(len(st.session_state.participants))
        for idx, (person, amount) in enumerate(tagihan.items()):
            cols_t[idx].metric(f"👤 {person}", format_rupiah(amount))

        total_check = sum(tagihan.values())
        if abs(total_check - total_bill) < 10:
            st.success(f"Total = {format_rupiah(total_check)} (sesuai total bill!)")
        else:
            st.warning(f"Total = {format_rupiah(total_check)} | Bill = {format_rupiah(total_bill)}")
