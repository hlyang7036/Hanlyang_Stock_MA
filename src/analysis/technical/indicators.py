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

# TODO: 다음 단계에서 구현할 함수들
# - calculate_macd()
# - calculate_triple_macd()
# - detect_peakout()
# - calculate_slope()
# - check_direction()
# - calculate_all_indicators()