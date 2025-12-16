  
# 필요한 라이브러리
import streamlit as st
import FinanceDataReader as fdr
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, date
from streamlit_lottie import st_lottie
import requests
from bs4 import BeautifulSoup



# 로티 붙이기
@st.cache_data
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()
lottie_url = "https://lottie.host/ec84bdca-8c08-41de-90cc-9bd58157f679/ooMiQcJ1eO.json"
lottie_json = load_lottieurl(lottie_url)




# 메인 타이틀
col2,col1 = st.columns([0.3, 0.7])
with col1: st.markdown("## 📈 **주식 차트** 📉")
with col2: st_lottie(lottie_json, speed=2, loop=True, width=100, height=100)
''
''



# 강사님이 지정해주신 함수(시장 데이터 읽어오는 함수) + 캐시 추가로 최적화
@st.cache_data
def getData(code, datestart, dateend):
    df = fdr.DataReader(code, datestart, dateend ).drop(columns='Change')  # 불필요한 'Change' 컬럼은 버린다.
    return df

@st.cache_data
def getSymbols(market='KOSPI', sort='Marcap'):
    df = fdr.StockListing(market)
    ascending = False if sort == 'Marcap' else True
    df.sort_values(by=[sort], ascending = ascending, inplace=True)
    return df[ ['Code', 'Name', 'Market'] ]

@st.cache_data(ttl=1800)  # 구글 뉴스 불러오는 함수(RSS 사용, 30분캐시)
def get_google_news(stock_name, max_news=3):
    query = stock_name.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query}+주식&hl=ko&gl=KR&ceid=KR:ko"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "xml")
    items = soup.find_all("item")[:max_news]

    news_list = []
    for item in items:
        title = item.title.text
        link = item.link.text
        pub_date = item.pubDate.text

        news_list.append({
            "title": title,
            "link": link,
            "date": pub_date})
    return news_list

def addBollingerBand(data, ax):
    # 추가적인 그래프 출력에 유리한 형태로 데이터프레임 변환.
    df = data.reset_index(drop=True)
    df['MA20'] = df['Close'].rolling(window=20).mean()  # 20일 이동평균.
    df['StDev'] = df['Close'].rolling(window=20).std()  # 20일 이동표준편차.
    df['Upper'] = df['MA20'] + (df['StDev'] * 2)        # 밴드의 상한.
    df['Lower'] = df['MA20'] - (df['StDev'] * 2)        # 밴드의 하한.
    df = df[19:]                                        # 시작일 20 이후만 가능. 
    ax.plot(df.index, df['Upper'], color = 'red', linestyle ='--', linewidth=1.5, label = 'Upper')       
    ax.plot(df.index, df['MA20'], color='aqua', linestyle = ':', linewidth = 2, label = 'MA20')
    ax.plot(df.index, df['Lower'], color='blue', linestyle= '--', linewidth=1.5, label = 'Lower')
    ax.fill_between(df.index, df['Upper'], df['Lower'], color='grey', alpha=0.3) 
    ax.legend(loc='best')



# 사이드바 (Sidebar) - 폼
with st.sidebar:
    st.header("⚙️ 차트 설정")
    ''
     # 위젯 : selectbox.(종목 마켓 선택)
    z = st.selectbox( '마켓을 선택해주세요.' , ['KOSPI', 'KOSDAQ','KONEX'] )
    symbols = getSymbols(z)
    symbols['Display'] = symbols['Name'] + " (" + symbols['Code'] + ")"
    e2 = st.empty()

    with st.form(key='myForm1', clear_on_submit=False):

        selected_name = st.selectbox("종목 선택", symbols['Display'])
        selected_code = selected_name.split("(")[-1].replace(")", "")

        #날짜 입력(시작일/종료일 설정)
        date_start = st.date_input("시작일 입력", 
            (datetime.today() - timedelta(days=365)).date())
        date_end = st.date_input("종료일 입력", datetime.today().date())

        #차트 유형 선택
        chart_type = st.selectbox("차트 유형(type)",["candle", "ohlc", "line"])
        chart_style = st.selectbox("차트 스타일(style)",["default", "binance", "yahoo"])

        #볼린저 밴드 표시 체크박스 추가
        show_bollinger = st.checkbox("볼린저밴드 표시", value=True)

        ''
        if date_start > date_end:
            st.error("시작일이 종료일보다 늦습니다. 다시 선택해주세요!")
        submitted = st.form_submit_button('확인')




# 메인 주식 그래프 (확인 버튼 누르면 활성화)
df = getData(selected_code, date_start, date_end) 
if submitted:
    
    st.subheader(f"▪️선택 종목  : :blue[{selected_name} (**{z}**) ]")
    marketcolors = mpf.make_marketcolors(up='red', down='blue', ohlc={'up': 'red', 'down': 'blue'})     
    mpf_style = mpf.make_mpf_style(base_mpf_style=chart_style, marketcolors=marketcolors)

    fig, ax = mpf.plot(
        data=df,                             # 받아온 데이터.      
        volume=False,                        # True 또는 False.                   
        type=chart_type,                    
        style=mpf_style,                     # 위에서 정의.
        figsize=(10,7),
        fontscale=1.1,
        mav=(5,10,30),                       # 이동평균선 (mav) 3개. 5일/10일/30일
        mavcolors=('red','green','blue'),    # 이동평균선 색상.
        returnfig=True)                      # Figure 객체 반환.

    if show_bollinger:
        addBollingerBand(df, ax[0])
    st.pyplot(fig)

''
''
''


# 메인그래프 밑에 종목회사 관련정보들 (추가하고 싶은 정보들 tab으로 추가 가능)
tab1, tab2, tab3, tab4, tab5  = st.tabs(
    ['**요약** :speech_balloon:', '**기간별 통계분석** :speech_balloon:', '**뉴스** :speech_balloon:',
     '**거래량** :speech_balloon:', '**투자 지표** :speech_balloon:'])


with tab1: # 요약
   
    # 장시작가격(시가):open, 그날최대가(고가):high, 그날최저가(저가):low, 그날최종가(종가):close
    # 데이터 로드에 성공하면(데이터프레임에 데이터가 있다면 실행)
    if not df.empty:
        latest_close = df['Close'].iloc[-1]    # 내가 선택한 종료일의 주식 종료값(종가)의 가장 마지막에 있는 숫자 뽑아내기
        period_high = df['Close'].max()        # 선택기간 내 최대값을 찾아서 저장
        period_low = df['Close'].min()         # 최소값을 찾아서 저장
        start_price = df['Close'].iloc[0]
        end_price = df['Close'].iloc[-1]
        return_pct = (end_price - start_price) / start_price * 100
        
        # -(하이픈)사용을 위해 마크다운 사용
        ''
        st.markdown(f"- **종목명:** {selected_name.split(' ')[0]}")
        st.markdown(f"- **종목 코드:** {selected_code}")
        st.markdown(f"- **최신 종가:** {latest_close:,.0f} 원")         # ,.0f:세자리마다 쉼표, 정수로 표시
        st.markdown(f"- **기간 내 최고가:** {period_high:,.0f} 원")
        st.markdown(f"- **기간 내 최저가:** {period_low:,.0f} 원")
        if return_pct > 0:
             st.markdown(f"- **선택 기간 수익률:** :red[{return_pct:.2f}%] 📈")
        elif return_pct < 0:
             st.markdown(f"- **선택 기간 수익률:** :blue[{return_pct:.2f}%] 📉")
        else:
             st.markdown(f"- **선택 기간 수익률:** {return_pct:.2f}%")

    # 데이터 로드에 실패했을때 실행
    else:          
        st.info("데이터가 없어 요약 정보를 표시할 수 없습니다.")




with tab2: # 기간별 통계분석
    ''
    st.markdown(f"#### '{selected_name}' 기간 통계 분석 :smile:")
    
    # df.empty 체크
    if not df.empty and len(df) >= 2: 
        
        latest_close = df['Close'].iloc[-1]     # 가장 최근 종가
        period_mean = df['Close'].mean()        # 선택 기간의 평균값
        period_max = df['Close'].max()          # 고가
        period_min = df['Close'].min()          # 저가
        
        st.markdown("---")
        # 첫번째, 평균과 비교할 때 현재 주가 위치
        st.markdown("##### **1. 현재 주가 위치**")
        
        # 현재 종가가 평균보다 높은지 낮은지 판단
        # 현재종가가 기간평균보다 높으면 
        if latest_close > period_mean:
            st.markdown(f"📈 **현재 종가** ({latest_close:,.0f}원)는 **선택된 기간 평균** ({period_mean:,.0f}원)보다 **높습니다.**")
        # 현재종가가 기간평균보다 낮으면
        elif latest_close < period_mean:
            st.markdown(f"📉 **현재 종가** ({latest_close:,.0f}원)는 기간 평균 ({period_mean:,.0f}원)보다 **낮습니다.**")
        # 수치가 비슷하면(같을때)
        else:
            st.info(f"현재 종가가 기간 평균과 거의 같습니다.")
            # info로 할때 파란색글자 출력이 되어 같다는 정보를 강조하기 위해 사용됨.


        st.markdown("---")
        #두번째, 내가 선택한 기간에 대한 가격비교
        st.markdown("##### **2. 기간 내 가격 분포**")
        
        # 최고/최저가와 현재 종가 비교
        price_range = period_max - period_min
        
        st.markdown(f"- **최고가**: :red[{period_max:,.0f}] 원")
        st.markdown(f"- **최저가**: :blue[{period_min:,.0f}] 원")
        st.markdown(f"- **금액 차이**: {price_range:,.0f} 원")
        
        st.markdown(f"현재 종가는 최저가 대비 **{(latest_close - period_min) / price_range * 100:.1f}%** 지점에 있습니다.")
        
    else:
        st.info("기간 통계를 계산하기 위한 데이터가 부족합니다.")




with tab3: # 뉴스


    tab1, tab2 = st.tabs(["국내", "국외"])
    with tab1:
        st.subheader("국내 증시 뉴스")
        naver_url = f'https://finance.naver.com/item/main.naver?code={selected_code}' 
        ''
        st.markdown(f"#### ***✅ N Pay 증권 '{selected_name.split('(')[0]}' 검색결과***")
    
        st.markdown(f"[N pay증권 {selected_name} 바로가기]({naver_url})")

        st.markdown("---")

        # 구글에서 뉴스 헤더 3개 가져오기
        st.markdown("#### 📰 ***관련 최신 뉴스 (Google)***")

        try:
            stock_name_only = selected_name.split("(")[0]
            news_list = get_google_news(stock_name_only, max_news=3)

            if news_list:
                for news in news_list:
                    st.markdown(
                        f"- **[{news['title']}]({news['link']})**  \n"
                        f"  <span style='color:gray'>{news['date']}</span>",
                        unsafe_allow_html=True
                    )
            else:
                st.info("관련 뉴스가 없습니다.")

        except Exception as e:
            st.error("뉴스를 불러오는 중 오류가 발생했습니다.")
    with tab2:
        st.subheader("국외 증시 뉴스")
        
        st.markdown("#### :newspaper: :gray[The Wall Street Journel ]")
        WSJ_url = f"https://www.wsj.com/market-data/quotes/KR/XKRX/{selected_code}?mod=searchresults_companyquotes"
        link_text = f" 월스트리트 저널에서 '{selected_name.split('(')[0]}' 검색결과 바로가기"
        st.markdown(f"[{link_text}]({WSJ_url})")
        st.warning("⚠️ 종목에 따라 뉴스 정보가 존재하지 않을 수도 있습니다.")

        st.markdown("---")

        st.markdown("#### :newspaper: :gray[Bloomberg Markets]")
        blm_url = "https://www.bloomberg.com/markets"
        st.markdown(f" - [블룸버그 마켓 섹션 구경하기]({blm_url})")
        ''
        ''
        st.markdown("#### :newspaper: :gray[Reuters News]")
        reu_url = "https://www.reuters.com/markets/"
        st.markdown(f" - [로이터 뉴스 속보 둘러보기]({reu_url})")



with tab4: # 거래량
    ''
    # 1. 작은 거래량 그래프
    volume_addplot = mpf.make_addplot(
        df['Volume'].values, 
        type='bar', 
        panel=0,           
        color='blue',      
        alpha=0.7, 
        ylabel='Volume_bar',
        )

    fig_volume, ax_volume = mpf.plot(
        data=df,
        volume=False,
        type='line',
        style=chart_style,
        figsize=(10, 4),   
        returnfig=True,
        addplot=volume_addplot,
        mav=()
        )
    st.pyplot(fig_volume)

    # 2. 거래량 통계자료
    st.markdown("---")
    st.markdown("#### 📊 거래량 주요 통계")
    ''
    avg_volume = df['Volume'].mean()    # 평균 거래량 계산
    max_volume_date = df['Volume'].idxmax().strftime('%Y년 %m월 %d일')   # 최대 거래량 날짜, 값 찾기
    max_volume = df['Volume'].max()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="평균 거래량", 
            value=f"{int(avg_volume):,}" )
        
    with col2:
        st.metric(
            label="최대 거래량", 
            value=f"{int(max_volume):,}" )
        
    with col3:
        st.markdown(f"**최대 거래량 날짜**")
        st.write(f"**{max_volume_date}**")

    if df['Volume'].iloc[-1] > avg_volume * 1.5:
        st.warning("최근 거래량이 평균 대비 크게 증가했습니다.")
    else:
        st.info("거래량은 평균 수준입니다.")




with tab5: # 투자 지표

    if not df.empty and len(df) >= 20:
        ''
        # 기간 수익률, 변동성
        close = df['Close']
        returns = close.pct_change().dropna()

        period_return = (close.iloc[-1] / close.iloc[0] - 1) * 100
        volatility = returns.std() * (252 ** 0.5) * 100  # 연환산

        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "📆 기간 수익률",
                f"{period_return:.2f} %",
                delta=None)
        with col2:
            st.metric(
                "⚠️ 연환산 변동성",
                f"{volatility:.2f} %",
                delta=None)
        st.markdown("---")


        # RSI 지표
        st.markdown("#### ▪️ RSI (상대강도지수)")

        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_latest = rsi.iloc[-1]

        if rsi_latest >= 70:
            st.error(f"RSI {rsi_latest:.1f} → 과매수 구간")
        elif rsi_latest <= 30:
            st.info(f"RSI {rsi_latest:.1f} → 과매도 구간")
        else:
            st.success(f"RSI {rsi_latest:.1f} → 중립 구간")


        # 최근 n일 수익률
        st.markdown("---")
        st.markdown("#### ▪️ 최근 수익률")

        col1, col2, col3 = st.columns(3)

        for col, n in zip([col1, col2, col3], [1, 5, 20]):
            recent_return = (
                close.iloc[-1] / close.iloc[-n-1] - 1) * 100

            with col:
                st.metric(
                    f"{n}일 수익률",
                    f"{recent_return:.2f} %",)
    
     
    else:
        st.info("지표 계산을 위한 데이터가 부족합니다. (최소 20일 이상 필요)")