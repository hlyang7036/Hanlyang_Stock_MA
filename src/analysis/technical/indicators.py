"""
기술적 지표 계산 모듈

이동평균선 투자법 전략에 필요한 기술적 지표들을 계산합니다.
- EMA (Exponential Moving Average): 지수 이동평균
- SMA (Simple Moving Average): 단순 이동평균
- MACD (Moving Average Convergence Divergence): 이동평균 수렴확산
- ATR (Average True Range): 평균 진폭
"""

import pandas as pd
import numpy as np
from typing import Union, Tuple
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_ema(
        data: Union[pd.Series, pd.DataFrame],
        period: int,
        column: str = 'Close'
) -> pd.Series:
    """
    지수 이동평균(EMA) 계산

    EMA는 최근 가격에 더 높은 가중치를 부여하는 이동평균입니다.
    SMA와 달리 최근 추세를 더 민감하게 반영합니다.

    계산식:
        EMA = [어제의 EMA × (n-1) + 오늘의 가격 × 2] / (n+1)

    Args:
        data (pd.Series | pd.DataFrame): 가격 데이터
            - Series: 직접 가격 데이터
            - DataFrame: 'Close' 컬럼 사용 (또는 column 파라미터 지정)
        period (int): EMA 계산 기간 (예: 5, 20, 40)
        column (str): DataFrame 사용 시 계산할 컬럼명 (기본값: 'Close')

    Returns:
        pd.Series: EMA 값 (원본 데이터와 동일한 인덱스)

    Raises:
        ValueError: 데이터 길이가 기간보다 짧을 경우
        TypeError: 지원하지 않는 데이터 타입

    Examples:
        >>> df = pd.DataFrame({'Close': [100, 102, 104, 103, 105]})
        >>> ema_5 = calculate_ema(df, period=5)
        >>> print(ema_5)

        >>> # Series로 직접 전달
        >>> ema_20 = calculate_ema(df['Close'], period=20)

    Notes:
        - pandas의 ewm() 메서드 사용 (span=period)
        - 초기값은 SMA로 계산 (warmup period)
        - 최소 period 이상의 데이터 필요
    """
    try:
        # 입력 데이터 처리
        if isinstance(data, pd.DataFrame):
            if column not in data.columns:
                raise ValueError(f"컬럼 '{column}'이 DataFrame에 없습니다. 사용 가능한 컬럼: {list(data.columns)}")
            series = data[column]
        elif isinstance(data, pd.Series):
            series = data
        else:
            raise TypeError(f"지원하지 않는 데이터 타입: {type(data)}. pd.Series 또는 pd.DataFrame을 사용하세요.")

        # 데이터 길이 검증
        if len(series) < period:
            raise ValueError(f"데이터 길이({len(series)})가 기간({period})보다 짧습니다.")

        # EMA 계산 (pandas ewm 사용)
        # span=period: EMA의 기간 설정
        # adjust=False: 재귀적 계산 방식 (표준 EMA 공식)
        # min_periods=period: 최소 period 개의 데이터가 있어야 계산 시작
        ema = series.ewm(span=period, adjust=False, min_periods=period).mean()

        logger.debug(f"EMA({period}) 계산 완료: {len(ema)}개 값")

        return ema

    except Exception as e:
        logger.error(f"EMA 계산 중 오류 발생: {e}")
        raise


def calculate_sma(
        data: Union[pd.Series, pd.DataFrame],
        period: int,
        column: str = 'Close'
) -> pd.Series:
    """
    단순 이동평균(SMA) 계산

    n일 동안의 가격을 합산하여 n으로 나눈 평균값입니다.
    EMA의 초기값 계산이나 참고용으로 사용됩니다.

    계산식:
        SMA = (P₁ + P₂ + ... + Pₙ) / n

    Args:
        data (pd.Series | pd.DataFrame): 가격 데이터
        period (int): SMA 계산 기간
        column (str): DataFrame 사용 시 계산할 컬럼명

    Returns:
        pd.Series: SMA 값

    Examples:
        >>> df = pd.DataFrame({'Close': [100, 102, 104, 103, 105]})
        >>> sma_5 = calculate_sma(df, period=5)
    """
    try:
        # 입력 데이터 처리
        if isinstance(data, pd.DataFrame):
            if column not in data.columns:
                raise ValueError(f"컬럼 '{column}'이 DataFrame에 없습니다.")
            series = data[column]
        elif isinstance(data, pd.Series):
            series = data
        else:
            raise TypeError(f"지원하지 않는 데이터 타입: {type(data)}")

        # 데이터 길이 검증
        if len(series) < period:
            raise ValueError(f"데이터 길이({len(series)})가 기간({period})보다 짧습니다.")

        # SMA 계산
        sma = series.rolling(window=period, min_periods=period).mean()

        logger.debug(f"SMA({period}) 계산 완료: {len(sma)}개 값")

        return sma

    except Exception as e:
        logger.error(f"SMA 계산 중 오류 발생: {e}")
        raise


def calculate_true_range(data: pd.DataFrame) -> pd.Series:
    """
    True Range 계산 (ATR의 구성 요소)

    True Range는 다음 세 가지 중 최댓값입니다:
    1. 당일 고가 - 당일 저가
    2. |당일 고가 - 전일 종가|
    3. |당일 저가 - 전일 종가|

    Args:
        data (pd.DataFrame): OHLC 데이터 (High, Low, Close 컬럼 필요)

    Returns:
        pd.Series: True Range 값

    Raises:
        ValueError: 필수 컬럼이 없을 경우

    Examples:
        >>> df = pd.DataFrame({
        ...     'High': [105, 107, 106],
        ...     'Low': [100, 102, 101],
        ...     'Close': [103, 105, 104]
        ... })
        >>> tr = calculate_true_range(df)

    Notes:
        - 첫 번째 행은 전일 종가가 없으므로 (고가 - 저가)만 계산
        - ATR 계산의 기초가 되는 지표
    """
    try:
        # 필수 컬럼 확인
        required_columns = ['High', 'Low', 'Close']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")

        # 전일 종가
        prev_close = data['Close'].shift(1)

        # True Range 계산
        # 1. 당일 고가 - 당일 저가
        high_low = data['High'] - data['Low']

        # 2. |당일 고가 - 전일 종가|
        high_prev_close = (data['High'] - prev_close).abs()

        # 3. |당일 저가 - 전일 종가|
        low_prev_close = (data['Low'] - prev_close).abs()

        # 세 값 중 최댓값
        true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)

        logger.debug(f"True Range 계산 완료: {len(true_range)}개 값")

        return true_range

    except Exception as e:
        logger.error(f"True Range 계산 중 오류 발생: {e}")
        raise


def calculate_atr(
        data: pd.DataFrame,
        period: int = 20
) -> pd.Series:
    """
    ATR (Average True Range) 계산

    ATR은 N일간의 True Range 평균으로, 변동성을 측정하는 지표입니다.
    포지션 사이징에 사용됩니다 (1유닛 = 계좌잔고 × 1% / ATR).

    계산식:
        1. True Range = Max(고가-저가, |고가-전일종가|, |저가-전일종가|)
        2. ATR = N일 True Range의 이동평균 (일반적으로 N=20)

    Args:
        data (pd.DataFrame): OHLC 데이터 (High, Low, Close 컬럼 필요)
        period (int): ATR 계산 기간 (기본값: 20일)

    Returns:
        pd.Series: ATR 값

    Raises:
        ValueError: 필수 컬럼이 없거나 데이터가 부족한 경우

    Examples:
        >>> df = pd.DataFrame({
        ...     'High': [105, 107, 106, 108, 110],
        ...     'Low': [100, 102, 101, 103, 105],
        ...     'Close': [103, 105, 104, 106, 108]
        ... })
        >>> atr_20 = calculate_atr(df, period=20)

        >>> # 포지션 사이징 예시
        >>> account_balance = 10_000_000  # 1천만원
        >>> current_atr = atr_20.iloc[-1]
        >>> unit_size = (account_balance * 0.01) / current_atr
        >>> print(f"1유닛: {unit_size:.0f}주")

    Notes:
        - 일반적으로 20일 기간 사용 (터틀 트레이딩 기법)
        - 변동성이 클수록 ATR 값이 커짐
        - 손절/익절 라인 설정 시 2ATR 사용
    """
    try:
        # 데이터 길이 검증
        if len(data) < period + 1:  # True Range 계산에 1일 필요
            raise ValueError(f"데이터 길이({len(data)})가 부족합니다. 최소 {period + 1}일 필요합니다.")

        # True Range 계산
        true_range = calculate_true_range(data)

        # ATR 계산 (True Range의 이동평균)
        # 첫 ATR은 SMA로 계산, 이후는 EMA 방식 사용
        atr = true_range.ewm(span=period, adjust=False, min_periods=period).mean()

        logger.debug(f"ATR({period}) 계산 완료: {len(atr)}개 값")

        return atr

    except Exception as e:
        logger.error(f"ATR 계산 중 오류 발생: {e}")
        raise


def calculate_macd(
        data: Union[pd.Series, pd.DataFrame],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        column: str = 'Close'
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence) 계산

    MACD는 두 개의 EMA 차이를 통해 추세의 방향과 강도를 파악하는 지표입니다.

    계산식:
        1. MACD선 = 단기 EMA - 장기 EMA
        2. 시그널선 = MACD의 signal일 EMA
        3. 히스토그램 = MACD - 시그널

    Args:
        data (pd.Series | pd.DataFrame): 가격 데이터
        fast (int): 단기 EMA 기간 (기본값: 12)
        slow (int): 장기 EMA 기간 (기본값: 26)
        signal (int): 시그널선 EMA 기간 (기본값: 9)
        column (str): DataFrame 사용 시 계산할 컬럼명

    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (MACD선, 시그널선, 히스토그램)

    Raises:
        ValueError: 데이터 길이가 부족하거나 파라미터가 잘못된 경우

    Examples:
        >>> df = pd.DataFrame({'Close': [100 + i for i in range(50)]})
        >>> macd, signal, hist = calculate_macd(df, fast=12, slow=26, signal=9)
        >>> print(f"MACD: {macd.iloc[-1]:.2f}")
        >>> print(f"Signal: {signal.iloc[-1]:.2f}")
        >>> print(f"Histogram: {hist.iloc[-1]:.2f}")

        >>> # 커스텀 파라미터 (5|20|9)
        >>> macd, signal, hist = calculate_macd(df, fast=5, slow=20, signal=9)

    Notes:
        - 0선 교차: MACD가 0을 교차 = 단기선과 장기선의 교차
        - 시그널 교차: MACD와 시그널 교차 = 매매 신호
        - 히스토그램: MACD 방향성 예측 (확대/축소)
        - 표준 설정: 12|26|9 (제럴드 아펜)
    """
    try:
        # 파라미터 검증
        if fast >= slow:
            raise ValueError(f"fast({fast})는 slow({slow})보다 작아야 합니다.")

        # 입력 데이터 처리
        if isinstance(data, pd.DataFrame):
            if column not in data.columns:
                raise ValueError(f"컬럼 '{column}'이 DataFrame에 없습니다.")
            series = data[column]
        elif isinstance(data, pd.Series):
            series = data
        else:
            raise TypeError(f"지원하지 않는 데이터 타입: {type(data)}")

        # 최소 데이터 길이 검증
        min_length = slow + signal
        if len(series) < min_length:
            raise ValueError(
                f"데이터 길이({len(series)})가 부족합니다. "
                f"최소 {min_length}일 필요합니다 (slow={slow} + signal={signal})."
            )

        # 1. 단기/장기 EMA 계산
        ema_fast = calculate_ema(series, period=fast)
        ema_slow = calculate_ema(series, period=slow)

        # 2. MACD선 계산
        macd_line = ema_fast - ema_slow

        # 3. 시그널선 계산 (MACD의 EMA)
        signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()

        # 4. 히스토그램 계산
        histogram = macd_line - signal_line

        logger.debug(
            f"MACD({fast}|{slow}|{signal}) 계산 완료: "
            f"MACD={len(macd_line)}개, Signal={len(signal_line)}개, Hist={len(histogram)}개"
        )

        return macd_line, signal_line, histogram

    except Exception as e:
        logger.error(f"MACD 계산 중 오류 발생: {e}")
        raise


def calculate_triple_macd(
        data: Union[pd.Series, pd.DataFrame],
        column: str = 'Close'
) -> pd.DataFrame:
    """
    3종 MACD 동시 계산 (대순환 분석용)

    이동평균선 대순환 분석을 위한 3개의 MACD를 동시에 계산합니다.
    각 MACD는 서로 다른 이동평균선 쌍의 관계를 나타냅니다.

    MACD 구성:
        - MACD(상): 5|20|9 - 단기선(5)과 중기선(20)의 관계
        - MACD(중): 5|40|9 - 단기선(5)과 장기선(40)의 관계
        - MACD(하): 20|40|9 - 중기선(20)과 장기선(40)의 관계

    Args:
        data (pd.Series | pd.DataFrame): 가격 데이터
        column (str): DataFrame 사용 시 계산할 컬럼명

    Returns:
        pd.DataFrame: 9개 컬럼을 가진 DataFrame
            - MACD_상, Signal_상, Hist_상
            - MACD_중, Signal_중, Hist_중
            - MACD_하, Signal_하, Hist_하

    Raises:
        ValueError: 데이터 길이가 부족한 경우 (최소 49일 필요)

    Examples:
        >>> df = pd.DataFrame({'Close': [100 + i for i in range(100)]})
        >>> triple_macd = calculate_triple_macd(df)
        >>> print(triple_macd.columns)
        Index(['MACD_상', 'Signal_상', 'Hist_상',
               'MACD_중', 'Signal_중', 'Hist_중',
               'MACD_하', 'Signal_하', 'Hist_하'], dtype='object')

        >>> # 최근 상태 확인
        >>> latest = triple_macd.iloc[-1]
        >>> print(f"MACD(상): {latest['MACD_상']:.2f}")
        >>> print(f"MACD(중): {latest['MACD_중']:.2f}")
        >>> print(f"MACD(하): {latest['MACD_하']:.2f}")

    Notes:
        - 6개 스테이지 판단에 필수적인 지표
        - MACD 0선 교차 = 해당 이동평균선 쌍의 교차
        - 3개 MACD 방향이 일치할 때 신뢰도 최대
        - 최소 49일 데이터 필요 (40 + 9)
    """
    try:
        # 입력 데이터 처리
        if isinstance(data, pd.DataFrame):
            if column not in data.columns:
                raise ValueError(f"컬럼 '{column}'이 DataFrame에 없습니다.")
            series = data[column]
            index = data.index
        elif isinstance(data, pd.Series):
            series = data
            index = data.index
        else:
            raise TypeError(f"지원하지 않는 데이터 타입: {type(data)}")

        # 최소 데이터 길이 검증 (40 + 9 = 49)
        min_length = 49
        if len(series) < min_length:
            raise ValueError(
                f"데이터 길이({len(series)})가 부족합니다. "
                f"최소 {min_length}일 필요합니다."
            )

        # 결과 저장용 DataFrame
        result = pd.DataFrame(index=index)

        # 1. MACD(상): 5|20|9 (단기-중기 관계)
        macd_upper, signal_upper, hist_upper = calculate_macd(
            series, fast=5, slow=20, signal=9
        )
        result['MACD_상'] = macd_upper
        result['Signal_상'] = signal_upper
        result['Hist_상'] = hist_upper

        # 2. MACD(중): 5|40|9 (단기-장기 관계)
        macd_middle, signal_middle, hist_middle = calculate_macd(
            series, fast=5, slow=40, signal=9
        )
        result['MACD_중'] = macd_middle
        result['Signal_중'] = signal_middle
        result['Hist_중'] = hist_middle

        # 3. MACD(하): 20|40|9 (중기-장기 관계)
        macd_lower, signal_lower, hist_lower = calculate_macd(
            series, fast=20, slow=40, signal=9
        )
        result['MACD_하'] = macd_lower
        result['Signal_하'] = signal_lower
        result['Hist_하'] = hist_lower

        logger.debug(
            f"3종 MACD 계산 완료: {len(result)}행 × {len(result.columns)}열"
        )

        return result

    except Exception as e:
        logger.error(f"3종 MACD 계산 중 오류 발생: {e}")
        raise

def detect_peakout(
        series: pd.Series,
        direction: str = 'both',
        lookback: int = 3
) -> pd.Series:
    """
    피크아웃(Peakout) 감지 - 방향 전환 포인트 탐지
    
    피크아웃은 히스토그램이나 MACD선이 최고점 또는 최저점을 찍고
    방향을 전환하는 지점을 의미합니다. 청산 신호로 활용됩니다.
    
    감지 방법:
        - 고점 피크아웃: 현재 값 < lookback 기간 내 최댓값
        - 저점 피크아웃: 현재 값 > lookback 기간 내 최솟값
    
    Args:
        series (pd.Series): MACD선, 히스토그램 등의 시계열 데이터
        direction (str): 감지할 피크아웃 방향 (기본값: 'both')
            - 'both': 고점/저점 피크아웃 모두 감지
            - 'down': 고점 피크아웃만 감지 (하락 전환)
            - 'up': 저점 피크아웃만 감지 (상승 전환)
        lookback (int): 피크아웃 감지를 위한 lookback 기간 (기본값: 3)
    
    Returns:
        pd.Series: 피크아웃 신호 (boolean)
            - direction='both': 1 (고점), -1 (저점), 0 (없음)
            - direction='down': True (고점 피크아웃), False (없음)
            - direction='up': True (저점 피크아웃), False (없음)
    
    Raises:
        ValueError: lookback이 1보다 작거나 direction이 잘못된 경우
        TypeError: series가 pd.Series가 아닐 경우
    
    Examples:
        >>> # 히스토그램 피크아웃 감지 (양방향)
        >>> df = pd.DataFrame({'Close': [100, 102, 105, 103, 101, 99, 101, 103]})
        >>> macd, signal, hist = calculate_macd(df, fast=5, slow=10, signal=3)
        >>> peakout = detect_peakout(hist, direction='both', lookback=3)
        >>> print(peakout[peakout != 0])  # 피크아웃 지점만 출력
        
        >>> # 하락 피크아웃만 감지 (매수 포지션 청산용)
        >>> down_peakout = detect_peakout(hist, direction='down', lookback=3)
        >>> print(down_peakout[down_peakout])  # True인 지점만
        
        >>> # 상승 피크아웃만 감지 (매도 포지션 청산용)
        >>> up_peakout = detect_peakout(hist, direction='up', lookback=3)
    
    Notes:
        - 히스토그램 피크아웃: 경계 태세 (청산 1단계)
        - MACD선 피크아웃: 50% 청산 (청산 2단계)
        - MACD-시그널 교차: 100% 청산 (청산 3단계)
        - lookback이 클수록 더 확실한 피크아웃만 감지
    """
    try:
        # 입력 검증
        if not isinstance(series, pd.Series):
            raise TypeError(f"series는 pd.Series여야 합니다. 현재: {type(series)}")
        
        if direction not in ['both', 'down', 'up']:
            raise ValueError(f"direction은 'both', 'down', 'up' 중 하나여야 합니다: {direction}")
        
        if lookback < 1:
            raise ValueError(f"lookback은 1 이상이어야 합니다. 현재: {lookback}")
        
        if len(series) < lookback + 1:
            raise ValueError(
                f"데이터 길이({len(series)})가 부족합니다. "
                f"최소 {lookback + 1}개 필요합니다."
            )
        
        # lookback 기간 동안의 최댓값/최솟값 계산 (현재 포함)
        rolling_max = series.rolling(window=lookback + 1, min_periods=lookback + 1).max()
        rolling_min = series.rolling(window=lookback + 1, min_periods=lookback + 1).min()
        
        # 고점 피크아웃 감지
        # 조건: 직전 값이 윈도우의 최고점이고, 현재 하락
        prev_value = series.shift(1)
        prev_is_peak = prev_value == rolling_max
        is_declining = series < prev_value
        is_high_peakout = prev_is_peak & is_declining
        
        # 저점 피크아웃 감지
        # 조건: 직전 값이 윈도우의 최저점이고, 현재 상승
        prev_is_trough = prev_value == rolling_min
        is_rising = series > prev_value
        is_low_peakout = prev_is_trough & is_rising
        
        # direction에 따라 결과 생성
        if direction == 'both':
            # 양방향: 1, -1, 0 형식
            peakout = pd.Series(0, index=series.index)
            peakout[is_high_peakout] = 1   # 고점 피크아웃
            peakout[is_low_peakout] = -1   # 저점 피크아웃
            
            logger.debug(
                f"피크아웃 감지 완료 (both): "
                f"고점 {is_high_peakout.sum()}개, 저점 {is_low_peakout.sum()}개"
            )
        elif direction == 'down':
            # 하락 피크아웃만: boolean
            peakout = is_high_peakout
            
            logger.debug(
                f"피크아웃 감지 완료 (down): "
                f"고점 {is_high_peakout.sum()}개"
            )
        else:  # direction == 'up'
            # 상승 피크아웃만: boolean
            peakout = is_low_peakout
            
            logger.debug(
                f"피크아웃 감지 완료 (up): "
                f"저점 {is_low_peakout.sum()}개"
            )
        
        return peakout
    
    except Exception as e:
        logger.error(f"피크아웃 감지 중 오류 발생: {e}")
        raise


def calculate_slope(
        series: pd.Series,
        period: int = 5
) -> pd.Series:
    """
    기울기 계산 - 우상향/우하향 판단
    
    지정된 기간 동안의 선형 회귀 기울기를 계산하여
    추세의 방향과 강도를 수치화합니다.
    
    계산 방법:
        - 최근 period 기간의 선형 회귀 기울기
        - 양수: 우상향 (상승 추세)
        - 음수: 우하향 (하락 추세)
        - 0에 가까움: 횡보
    
    Args:
        series (pd.Series): MACD, 히스토그램 등의 시계열 데이터
        period (int): 기울기 계산 기간 (기본값: 5)
    
    Returns:
        pd.Series: 각 시점의 기울기 값
    
    Raises:
        ValueError: period가 2보다 작을 경우
        TypeError: series가 pd.Series가 아닐 경우
    
    Examples:
        >>> # MACD 기울기 계산
        >>> df = pd.DataFrame({'Close': [100 + i for i in range(50)]})
        >>> macd, signal, hist = calculate_macd(df, fast=5, slow=20, signal=9)
        >>> slope = calculate_slope(macd, period=5)
        >>> print(f"최근 기울기: {slope.iloc[-1]:.4f}")
        
        >>> # 히스토그램 기울기
        >>> hist_slope = calculate_slope(hist, period=5)
        >>> print("상승 추세" if hist_slope.iloc[-1] > 0 else "하락 추세")
    
    Notes:
        - 기울기 > 0: 우상향 (매수 신호 강화)
        - 기울기 < 0: 우하향 (매도 신호 강화)
        - 기울기 절댓값이 클수록 추세가 강함
        - 3개 MACD 기울기가 모두 동일 방향이면 신뢰도 최대
    """
    try:
        # 입력 검증
        if not isinstance(series, pd.Series):
            raise TypeError(f"series는 pd.Series여야 합니다. 현재: {type(series)}")
        
        if period < 2:
            raise ValueError(f"period는 2 이상이어야 합니다. 현재: {period}")
        
        if len(series) < period:
            raise ValueError(
                f"데이터 길이({len(series)})가 부족합니다. "
                f"최소 {period}개 필요합니다."
            )
        
        # 기울기 계산을 위한 함수
        def linear_regression_slope(y):
            """주어진 윈도우에서 선형 회귀 기울기 계산"""
            if len(y) < 2 or y.isna().all():
                return np.nan
            
            # x: 0, 1, 2, ..., period-1
            x = np.arange(len(y))
            
            # NaN 제거
            mask = ~np.isnan(y)
            if mask.sum() < 2:
                return np.nan
            
            x_clean = x[mask]
            y_clean = y[mask]
            
            # 선형 회귀: y = mx + b에서 m(기울기) 계산
            # m = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
            n = len(x_clean)
            sum_x = x_clean.sum()
            sum_y = y_clean.sum()
            sum_xy = (x_clean * y_clean).sum()
            sum_x2 = (x_clean ** 2).sum()
            
            denominator = n * sum_x2 - sum_x ** 2
            if denominator == 0:
                return 0.0
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            
            return slope
        
        # rolling window를 사용하여 각 시점의 기울기 계산
        slopes = series.rolling(window=period, min_periods=period).apply(
            linear_regression_slope, raw=False
        )
        
        logger.debug(f"기울기 계산 완료: period={period}, {len(slopes)}개 값")
        
        return slopes
    
    except Exception as e:
        logger.error(f"기울기 계산 중 오류 발생: {e}")
        raise


def check_direction(
        series: pd.Series,
        threshold: float = 0.0
) -> pd.Series:
    """
    방향 판단 - 'up', 'down', 'neutral' 분류
    
    시계열 데이터의 방향을 판단하여 문자열로 반환합니다.
    3개 MACD의 방향 일치 여부를 확인하는 데 사용됩니다.
    
    판단 기준:
        - 'up': series > threshold (우상향)
        - 'down': series < -threshold (우하향)
        - 'neutral': |series| <= threshold (횡보)
    
    Args:
        series (pd.Series): 방향을 판단할 시계열 데이터
        threshold (float): 중립 판단 기준값 (기본값: 0.0)
    
    Returns:
        pd.Series: 각 시점의 방향 ('up', 'down', 'neutral')
    
    Raises:
        ValueError: threshold가 음수일 경우
        TypeError: series가 pd.Series가 아닐 경우
    
    Examples:
        >>> # MACD 방향 판단
        >>> df = pd.DataFrame({'Close': [100, 102, 105, 103, 101]})
        >>> macd, signal, hist = calculate_macd(df, fast=5, slow=10, signal=3)
        >>> direction = check_direction(macd, threshold=0.0)
        >>> print(direction.iloc[-1])  # 'up' or 'down' or 'neutral'
        
        >>> # 3개 MACD 방향 일치 확인
        >>> triple_macd = calculate_triple_macd(df)
        >>> dir_upper = check_direction(triple_macd['MACD_상'])
        >>> dir_middle = check_direction(triple_macd['MACD_중'])
        >>> dir_lower = check_direction(triple_macd['MACD_하'])
        >>> 
        >>> # 모두 'up'이면 강한 매수 신호
        >>> all_up = (dir_upper == 'up') & (dir_middle == 'up') & (dir_lower == 'up')
        >>> print(f"강한 매수 신호: {all_up.iloc[-1]}")
    
    Notes:
        - 3개 MACD가 모두 'up': 강한 매수 신호
        - 3개 MACD가 모두 'down': 강한 매도 신호
        - 방향이 일치하지 않으면: 관망 또는 신중한 진입
        - threshold를 크게 설정하면 더 확실한 방향만 감지
    """
    try:
        # 입력 검증
        if not isinstance(series, pd.Series):
            raise TypeError(f"series는 pd.Series여야 합니다. 현재: {type(series)}")
        
        if threshold < 0:
            raise ValueError(f"threshold는 0 이상이어야 합니다. 현재: {threshold}")
        
        # 방향 판단
        direction = pd.Series('neutral', index=series.index)
        
        # 우상향
        direction[series > threshold] = 'up'
        
        # 우하향
        direction[series < -threshold] = 'down'
        
        # 통계 정보
        up_count = (direction == 'up').sum()
        down_count = (direction == 'down').sum()
        neutral_count = (direction == 'neutral').sum()
        
        logger.debug(
            f"방향 판단 완료: up={up_count}, down={down_count}, neutral={neutral_count}"
        )
        
        return direction
    
    except Exception as e:
        logger.error(f"방향 판단 중 오류 발생: {e}")
        raise


def calculate_all_indicators(
        data: pd.DataFrame,
        ema_periods: Tuple[int, int, int] = (5, 20, 40),
        atr_period: int = 20,
        peakout_lookback: int = 3,
        slope_period: int = 5,
        direction_threshold: float = 0.0
) -> pd.DataFrame:
    """
    모든 기술적 지표를 DataFrame에 추가

    이동평균선 투자법 전략에 필요한 모든 지표를 한 번에 계산하여
    원본 DataFrame에 추가한 새로운 DataFrame을 반환합니다.

    계산되는 지표:
        1. EMA (5일, 20일, 40일)
        2. MACD 3종 (MACD선, 시그널선, 히스토그램)
           - MACD(상): 5|20|9
           - MACD(중): 5|40|9
           - MACD(하): 20|40|9
        3. ATR (변동성 지표)
        4. 피크아웃 (히스토그램, MACD선)
        5. 기울기 (3종 MACD)
        6. 방향성 (3종 MACD)

    Args:
        data (pd.DataFrame): OHLC 데이터 (Open, High, Low, Close, Volume 필요)
        ema_periods (Tuple[int, int, int]): EMA 기간 (기본값: (5, 20, 40))
        atr_period (int): ATR 계산 기간 (기본값: 20)
        peakout_lookback (int): 피크아웃 감지 lookback 기간 (기본값: 3)
        slope_period (int): 기울기 계산 기간 (기본값: 5)
        direction_threshold (float): 방향 판단 threshold (기본값: 0.0)

    Returns:
        pd.DataFrame: 원본 데이터 + 모든 지표가 추가된 DataFrame

    Raises:
        ValueError: 필수 컬럼이 없거나 데이터 길이가 부족한 경우
        TypeError: 데이터 타입이 올바르지 않은 경우

    Examples:
        >>> from src.data import get_stock_data
        >>>
        >>> # 데이터 수집
        >>> df = get_stock_data('005930', period=100)
        >>>
        >>> # 모든 지표 계산
        >>> df_with_indicators = calculate_all_indicators(df)
        >>>
        >>> # 결과 확인
        >>> print(df_with_indicators.columns)
        >>> print(df_with_indicators.tail())
        >>>
        >>> # 커스텀 설정
        >>> df_custom = calculate_all_indicators(
        ...     df,
        ...     ema_periods=(10, 30, 60),
        ...     atr_period=14,
        ...     peakout_lookback=5
        ... )

    Notes:
        - 최소 49일 이상의 데이터 필요 (MACD 계산 최소 요구사항)
        - 초기 기간의 일부 지표는 NaN 값을 가짐
        - 원본 DataFrame은 수정되지 않음 (복사본 생성)
        - 계산 순서: 기본 지표 → MACD → 파생 지표
    """
    try:
        # 입력 검증
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"data는 pd.DataFrame이어야 합니다. 현재: {type(data)}")

        # 필수 컬럼 확인
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")

        # 최소 데이터 길이 검증
        min_length = 49  # MACD(중/하) 계산 최소 요구사항
        if len(data) < min_length:
            raise ValueError(
                f"데이터 길이({len(data)})가 부족합니다. "
                f"최소 {min_length}일 필요합니다."
            )

        # 원본 데이터 복사
        result = data.copy()

        logger.info("모든 기술적 지표 계산 시작...")

        # 1. EMA 계산
        logger.debug("EMA 계산 중...")
        result['EMA_5'] = calculate_ema(data, period=ema_periods[0])
        result['EMA_20'] = calculate_ema(data, period=ema_periods[1])
        result['EMA_40'] = calculate_ema(data, period=ema_periods[2])

        # 2. ATR 계산
        logger.debug("ATR 계산 중...")
        result['ATR'] = calculate_atr(data, period=atr_period)

        # 3. MACD 3종 계산
        logger.debug("MACD 3종 계산 중...")
        triple_macd = calculate_triple_macd(data)
        result = pd.concat([result, triple_macd], axis=1)

        # 4. 피크아웃 감지
        logger.debug("피크아웃 감지 중...")
        # 히스토그램 피크아웃
        hist_upper = result['Hist_상'].dropna()
        if len(hist_upper) >= peakout_lookback + 1:
            result['Peakout_Hist_상'] = detect_peakout(hist_upper, lookback=peakout_lookback)

        hist_middle = result['Hist_중'].dropna()
        if len(hist_middle) >= peakout_lookback + 1:
            result['Peakout_Hist_중'] = detect_peakout(hist_middle, lookback=peakout_lookback)

        hist_lower = result['Hist_하'].dropna()
        if len(hist_lower) >= peakout_lookback + 1:
            result['Peakout_Hist_하'] = detect_peakout(hist_lower, lookback=peakout_lookback)

        # MACD선 피크아웃
        macd_upper = result['MACD_상'].dropna()
        if len(macd_upper) >= peakout_lookback + 1:
            result['Peakout_MACD_상'] = detect_peakout(macd_upper, lookback=peakout_lookback)

        macd_middle = result['MACD_중'].dropna()
        if len(macd_middle) >= peakout_lookback + 1:
            result['Peakout_MACD_중'] = detect_peakout(macd_middle, lookback=peakout_lookback)

        macd_lower = result['MACD_하'].dropna()
        if len(macd_lower) >= peakout_lookback + 1:
            result['Peakout_MACD_하'] = detect_peakout(macd_lower, lookback=peakout_lookback)

        # 5. 기울기 계산
        logger.debug("기울기 계산 중...")
        macd_upper_clean = result['MACD_상'].dropna()
        if len(macd_upper_clean) >= slope_period:
            result['Slope_MACD_상'] = calculate_slope(macd_upper_clean, period=slope_period)

        macd_middle_clean = result['MACD_중'].dropna()
        if len(macd_middle_clean) >= slope_period:
            result['Slope_MACD_중'] = calculate_slope(macd_middle_clean, period=slope_period)

        macd_lower_clean = result['MACD_하'].dropna()
        if len(macd_lower_clean) >= slope_period:
            result['Slope_MACD_하'] = calculate_slope(macd_lower_clean, period=slope_period)

        # 6. 방향 판단
        logger.debug("방향 판단 중...")
        result['Dir_MACD_상'] = check_direction(result['MACD_상'], threshold=direction_threshold)
        result['Dir_MACD_중'] = check_direction(result['MACD_중'], threshold=direction_threshold)
        result['Dir_MACD_하'] = check_direction(result['MACD_하'], threshold=direction_threshold)

        # 7. 통합 신호 생성
        logger.debug("통합 신호 생성 중...")
        # 3개 MACD 방향 일치 확인
        all_up = (
                (result['Dir_MACD_상'] == 'up') &
                (result['Dir_MACD_중'] == 'up') &
                (result['Dir_MACD_하'] == 'up')
        )

        all_down = (
                (result['Dir_MACD_상'] == 'down') &
                (result['Dir_MACD_중'] == 'down') &
                (result['Dir_MACD_하'] == 'down')
        )

        result['Direction_Agreement'] = 'mixed'
        result.loc[all_up, 'Direction_Agreement'] = 'all_up'
        result.loc[all_down, 'Direction_Agreement'] = 'all_down'

        logger.info(
            f"모든 기술적 지표 계산 완료: "
            f"{len(result)}행 × {len(result.columns)}열"
        )

        return result

    except Exception as e:
        logger.error(f"지표 계산 중 오류 발생: {e}")
        raise