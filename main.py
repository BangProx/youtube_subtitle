import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd
import openai
from openai import OpenAI
import os

api_key=os.getenv("OPENAI_API_KEY")
client = OpenAI()

def get_youtube_subtitle(youtube_url):
    try:
        # YouTube URL에서 video_id 추출
        video_id = youtube_url.split('v=')[1]
        if '&' in video_id:
            video_id = video_id.split('&')[0]
            
        # 자막 가져오기 시도 (수동 자막 -> 자동 생성 자막 순서로)
        try:
            # 먼저 수동 자막 시도
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        except:
            try:
                # 수동 자막이 없는 경우 자동 생성 자막 시도
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko-KR', 'en-US', 'en'])
            except:
                # 사용 가능한 모든 자막 목록 가져오기
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                # 첫 번째 사용 가능한 자막 선택
                first_transcript = next(iter(transcript_list._manually_created_transcripts.values()) or \
                                     iter(transcript_list._generated_transcripts.values()))
                # 한국어로 번역 시도
                try:
                    transcript_list = first_transcript.translate('ko').fetch()
                except:
                    # 번역이 안되면 원본 자막 사용
                    transcript_list = first_transcript.fetch()
        
        # 자막 텍스트만 추출하여 하나의 문자열로 결합
        subtitle_text = ' '.join([t['text'] for t in transcript_list])
        
        return subtitle_text, transcript_list
    
    except Exception as e:
        return f"자막을 가져오는 중 오류가 발생했습니다: {str(e)}", None
    

INSTRUCTIONS = {
    'organize' : {
        'instruction' : """
            Act as a professional content organizer. 
            Given YouTube subtitles, first identify the main topic and key points. 
            Then, organize the content according to the topic and key points without omitting any details. 
            Ensure the content is well-organized and aligns with the main topic.""",
        'file_suffix': 'organize'
    },
    'summarize' : {
        'instruction':  """
            Act as a professional content summarizer. 
            Given YouTube subtitles, first identify the main topic and key points. 
            Then, summarize the content according to the topic and key points without omitting key points. 
            Ensure the summary is well-organized and aligns with the main topic.""",
        'file_suffix': 'summarize'
    },
    'translate' : {
        'instruction' : """
            Act as a professional content translater. 
            Your role is to arrange the information to enhance Readability.
            DO NOT OMIT ANY DETAILS OR WORDS""",
        'file_suffix': 'translate'
    }
}

def llm(text,function_type):
    try:
        system_instruction = INSTRUCTIONS[function_type]['instruction']

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", 
                 "content": system_instruction},
                {"role": "user", 
                 "content": f"다음 내용을 한국어로 정리해주세요:\n\n{text}"}
            ],
            temperature=0
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"요약 중 오류가 발생했습니다: {str(e)}"
    

def main():
    st.title('YouTube 자막 다운로더')
    
    # YouTube URL을 세션 상태로 저장
    if 'youtube_url' not in st.session_state:
        st.session_state.youtube_url = ''
    
    # YouTube URL 입력 필드
    youtube_url = st.text_input('YouTube URL을 입력하세요', value=st.session_state.youtube_url)
    st.session_state.youtube_url = youtube_url
    
    if youtube_url:
        subtitle_text, transcript_list = get_youtube_subtitle(youtube_url)
        
        if transcript_list:
            # 자막 텍스트 출력
            st.subheader('자막 내용')
            st.text_area('전체 자막', subtitle_text, height=300)
            
            # 자막 데이터를 DataFrame으로 변환
            df = pd.DataFrame(transcript_list)
            
            # CSV 다운로드 버튼
            st.download_button(
                label="CSV로 다운로드",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name='youtube_subtiles.csv',
                mime='text/csv'
            )
            
            # TXT 다운로드 버튼
            st.download_button(
                label="TXT로 다운로드",
                data=subtitle_text.encode('utf-8'),
                file_name='youtube_subtiles.txt',
                mime='text/plain'
            )
            
            # 컬럼 생성
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("AI로 요약하기"):
                    summarize = llm(subtitle_text,"summarize")
                    st.session_state.summarize = summarize
                    st.session_state.show_summarize = True
            
            with col2:
                if st.button("AI로 정리하기"):
                    organize = llm(subtitle_text,"organize")
                    st.session_state.organize = organize
                    st.session_state.show_organize = True
            
            with col3:
                if st.button("AI로 번역하기"):
                    translate = llm(subtitle_text,"translate")
                    st.session_state.translate = translate
                    st.session_state.show_translate = True
            
            # 결과 표시
            if 'show_summarize' in st.session_state and st.session_state.show_summarize:
                st.subheader('AI 요약본')
                st.markdown(st.session_state.summarize)
                st.download_button(
                    label="요약본 다운로드",
                    data=st.session_state.summarize.encode('utf-8'),
                    file_name='youtube_subtiles_summarize.md',
                    mime='text/markdown'
                )
            
            if 'show_organize' in st.session_state and st.session_state.show_organize:
                st.subheader('AI 정리본')
                st.markdown(st.session_state.organize)
                st.download_button(
                    label="정리본 다운로드",
                    data=st.session_state.organize.encode('utf-8'),
                    file_name='youtube_subtiles_organize.md',
                    mime='text/markdown'
                )
            
            if 'show_translate' in st.session_state and st.session_state.show_translate:
                st.subheader('AI 번역본')
                st.markdown(st.session_state.translate)
                st.download_button(
                    label="번역본 다운로드",
                    data=st.session_state.translate.encode('utf-8'),
                    file_name='youtube_subtiles_translate.md',
                    mime='text/markdown'
                )

if __name__ == '__main__':
    main()