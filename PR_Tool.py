import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
import io
import re

# --- 頁面設定 ---
st.set_page_config(page_title="iesResearch PR Toolset 2026", layout="wide")

st.title("iesResearch PR Discovery & Filter Tool")
st.markdown("""
This utility automates media coverage discovery and cross-references results against the 
**iesResearch Master MediaOutlets**.
""")

# --- 清洗函數：剔除類別、STAFF、FREELANCE 及其後的數字 ---
def clean_media_outlets(df):
    raw_list = df[0].dropna().astype(str).tolist()
    cleaned = []
    
    # 定義要剔除的類別名稱 (根據你之前的名單)
    categories = [
        "Newspaper", "Magazine", "Trade Magazine", "Newsletter",
        "Tabloid","TV", "Radio", "Wire", "News Service/Syndicate",
        "Online", "Academic Journal", "Publisher", "Blog", "Other"
    ]
    
    skip_next = False
    
    for i, line in enumerate(raw_list):
        text = line.strip()
        
        # 1. 處理「下一行數字」邏輯：如果上一行是 STAFF/FREELANCE，這行就跳過
        if skip_next:
            skip_next = False
            continue
            
        # 2. 剔除空行
        if not text:
            continue
            
        # 3. 剔除 Category 關鍵字
        if text in categories:
            continue
            
        # 4. 剔除 STAFF 或 FREELANCE，並標記「跳過下一行」
        if text.upper() in ["STAFF", "FREELANCE"]:
            skip_next = True
            continue
            
        # 5. 確保這行不是純數字 (保險起見)
        if re.match(r'^\d+$', text):
            continue
            
        # 剩下的就是真正的媒體名稱
        cleaned.append(text)
        
    return cleaned

# --- Sidebar: Setup ---
with st.sidebar:
    st.header("Authentication & Data")
    api_key = st.text_input("SerpApi Key", type="password")
    
    st.markdown("---")
    st.header("Reference Benchmark")
    # 1. 改名為 MediaOutlets
    media_outlets_file = st.file_uploader("Upload CSV 1: MediaOutlets", type=["csv"])
    
    target_media = []
    if media_outlets_file:
        try:
            # 讀取原始資料
            raw_df = pd.read_csv(media_outlets_file, header=None, sep='|', engine='python', encoding='utf-8-sig')
            
            # 2. 執行清洗邏輯
            target_media = clean_media_outlets(raw_df)
            
            st.success(f"Successfully cleaned! Loaded {len(target_media)} Media Outlets.")
            
            # 讓使用者可以預覽清洗後的結果，確認 STAFF 跟數字不見了
            with st.expander("Preview Cleaned MediaOutlets"):
                st.write(target_media[:20]) # 顯示前 20 個
                
        except Exception as e:
            st.error(f"Error loading MediaOutlets: {e}")

# --- Main Section: Filters ---
st.header("Exclusion Filters")
st.write("Exclude non-media noise from the discovery results:")

col1, col2, col3, col4 = st.columns(4)
with col1:
    filter_newswise = st.checkbox("Newswise Official", value=True)
with col2:
    filter_fb = st.checkbox("Facebook", value=True)
with col3:
    filter_x = st.checkbox("X (Twitter)", value=True)
with col4:
    filter_social = st.checkbox("Other Social (IG, LinkedIn, YT)", value=True)

exclude_list = []
if filter_newswise: exclude_list.append("newswise.com")
if filter_fb: exclude_list.append("facebook.com")
if filter_x: exclude_list.extend(["x.com", "twitter.com"])
if filter_social: exclude_list.extend(["instagram.com", "linkedin.com", "youtube.com"])

st.markdown("---")

# --- Discovery Engine ---
st.header("Coverage Discovery Engine")
title_file = st.file_uploader("Upload CSV 2: Master Titles (Consolidated Search List)", type=["csv"])

if title_file and api_key:
    df_input = pd.read_csv(title_file)
    
    if st.button("Run Discovery Process"):
        if 'Title' not in df_input.columns:
            st.error("Error: CSV must contain a column named 'Title'.")
        else:
            titles = df_input['Title'].dropna().tolist()
            results_storage = []
            
            progress_bar = st.progress(0)
            status = st.empty()

            for i, title in enumerate(titles):
                status.text(f"Searching ({i+1}/{len(titles)}): {title[:50]}...")
                
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
                        is_excluded = any(domain in link for domain in exclude_list)
                        
                        if not is_excluded:
                            # 比對標籤改名為 In_iesResearch_Outlets
                            is_match = "Yes" if any(m.lower() in source.lower() for m in target_media if len(m) > 3) else "No"
                            
                            results_storage.append({
                                "Article_Title": title,
                                "Media_Outlet": source,
                                "In_iesResearch_Outlets": is_match,
                                "Link": res.get("link"),
                                "Snippet": res.get("snippet", "")
                            })
                except Exception as e:
                    st.warning(f"Error searching '{title}': {e}")
                
                progress_bar.progress((i + 1) / len(titles))

            if results_storage:
                df_res = pd.DataFrame(results_storage)
                st.subheader(f"Search Completed: {len(df_res)} Results Found")
                df_res = df_res.sort_values(by="In_iesResearch_Outlets", ascending=False)
                st.dataframe(df_res)

                csv_buffer = io.StringIO()
                df_res.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                st.download_button(
                    label="Download iesResearch Coverage Report (CSV)",
                    data=csv_buffer.getvalue(),
                    file_name="iesResearch_Coverage_Report.csv",
                    mime="text/csv"
                )
