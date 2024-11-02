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
            Your role is to arrange the information to enhance Readability.""",
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
                 "content": f"다음 내용을 한국어로 정리해주세요. 주요 개념 및 Jargon은 영어 표현을 사용해주세요.:\n\n{text}"}
            ],
            temperature=0
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"요약 중 오류가 발생했습니다: {str(e)}"
    

def main():
    st.title('YouTube 자막 다운로더')
    
    # YouTube URL 입력 필드
    youtube_url = st.text_input('YouTube URL을 입력하세요')
    
    if youtube_url:
        if st.button('자막 가져오기'):
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
                
                if st.button("AI로 요약하기"):
                    # 번역 실행
                    summarize = llm(subtitle_text,"summarize")
                    
                    # 요약본 화면에 표시
                    st.subheader('AI 정리본')
                    st.markdown(summarize)
                    
                    # 한국어로 요약하기 버튼
                    st.download_button(
                        label="AI로 정리하기",
                        data = summarize.encode('utf-8'),
                        file_name='youtube_subtiles_summarize.md',
                        mime='text/markdown'
                    )    
                
                if st.button("AI로 정리하기"):
                    # 정리 실행
                    organize = llm(subtitle_text,"organize")
                    
                    # 요약본 화면에 표시
                    st.subheader('AI 정리본')
                    st.markdown(organize)
                    
                    # 한국어로 요약하기 버튼
                    st.download_button(
                        label="AI로 정리하기",
                        data = organize.encode('utf-8'),
                        file_name='youtube_subtiles_organize.md',
                        mime='text/markdown'
                    )

                if st.button("AI로 번역하기"):
                    # 번역 실행
                    translate = llm(subtitle_text,"translate")
                    
                    # 요약본 화면에 표시
                    st.subheader('AI 정리본')
                    st.markdown(translate)
                    
                    # 한국어로 요약하기 버튼
                    st.download_button(
                        label="AI로 정리하기",
                        data = translate.encode('utf-8'),
                        file_name='youtube_subtiles_translate.md',
                        mime='text/markdown'
                    )
                
            else:
                st.error(subtitle_text)  # 에러 메시지 출력

if __name__ == '__main__':
    main()