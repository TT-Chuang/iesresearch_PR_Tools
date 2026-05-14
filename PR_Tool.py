import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import io

# --- UI Setup ---
st.set_page_config(page_title="iesResearch PR Analysis Tool", layout="wide")
st.title("iesResearch PR Analysis Tool")

# --- Sidebar: Data & API ---
with st.sidebar:
    st.header("🔑 Authentication & Data")
    api_key = st.text_input("SerpApi Key", type="password")
    
    st.markdown("---")
    st.header("📊 Media Reference List")
    media_list_file = st.file_uploader("Upload Raw Media CSV", type=["csv"])
    
    target_media = []
    if media_list_file:
        # 使用管道符號 | 讀取，完美避開媒體名稱內的逗號報錯
        raw_m_df = pd.read_csv(media_list_file, header=None, sep='|', engine='python', encoding='utf-8-sig')
        target_media = raw_m_df[0].dropna().astype(str).str.strip().tolist()
        st.success(f"Loaded {len(target_media)} media outlets.")

# --- Main Logic: Filter Selection ---
st.header("Filter Settings")
st.write("Select the platforms you want to **EXCLUDE** from the results:")

# 讓使用者自行選擇過濾項目
col1, col2, col3, col4 = st.columns(4)
with col1:
    filter_newswise = st.checkbox("Newswise", value=True)
with col2:
    filter_fb = st.checkbox("Facebook", value=True)
with col3:
    filter_x = st.checkbox("X (Twitter)", value=True)
with col4:
    filter_social = st.checkbox("Other Social (IG, LinkedIn, YT)", value=True)

# 建立動態過濾清單
exclude_list = []
if filter_newswise: exclude_list.append("newswise.com")
if filter_fb: exclude_list.append("facebook.com")
if filter_x: exclude_list.extend(["x.com", "twitter.com"])
if filter_social: exclude_list.extend(["instagram.com", "linkedin.com", "youtube.com"])

# 允許使用者輸入額外的排除關鍵字
extra_filters = st.text_input("Additional domains to exclude (comma separated, e.g., 'ezpr.com, pinterest.com')")
if extra_filters:
    exclude_list.extend([x.strip().lower() for x in extra_filters.split(",")])

st.markdown("---")

# --- Discovery Logic ---
title_file = st.file_uploader("Step 1: Upload Title CSV (Column: 'Title')", type=["csv"])

if title_file and api_key:
    df_input = pd.read_csv(title_file)
    
    if st.button("Step 2: Start Discovery"):
        titles = df_input['Title'].dropna().tolist()
        results_storage = []
        
        progress_bar = st.progress(0)
        status = st.empty()

        for i, title in enumerate(titles):
            status.text(f"Searching ({i+1}/{len(titles)}): {title[:60]}...")
            
            params = {
                "q": f'"{title.strip()}"',
                "engine": "google",
                "filter": "0", 
                "api_key": api_key
            }

            try:
                search = GoogleSearch(params)
                results = search.get_dict().get("organic_results", [])
                
                for res in results:
                    link = res.get("link", "").lower()
                    source = res.get("source", "Unknown")
                    
                    # 檢查是否符合過濾條件
                    is_excluded = any(domain in link for domain in exclude_list)
                    
                    if not is_excluded:
                        # 比對原始名單
                        is_match = "Yes" if any(m.lower() in source.lower() for m in target_media if len(m) > 3) else "No"
                        
                        results_storage.append({
                            "Article_Title": title,
                            "Media_Outlet": source,
                            "In_Report_List": is_match,
                            "Link": res.get("link"),
                            "Snippet": res.get("snippet", "")
                        })
            except Exception as e:
                st.error(f"Error at {title}: {e}")
            
            progress_bar.progress((i + 1) / len(titles))

        # --- Output ---
        if results_storage:
            df_res = pd.DataFrame(results_storage)
            st.subheader(f"✨ Found {len(df_res)} Clean Results")
            st.dataframe(df_res)

            csv_buffer = io.StringIO()
            df_res.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            st.download_button("📥 Download Filtered_Report.csv", data=csv_buffer.getvalue(), file_name="Filtered_Media_Report.csv")
        else:
            st.warning("No results found with the current filters.")