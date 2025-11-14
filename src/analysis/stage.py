"""
스테이지 분석 모듈

이 모듈은 이동평균선 배열과 MACD를 활용하여 6단계 스테이지를 판단합니다.

Functions:
    determine_ma_arrangement: 이동평균선 배열 순서 판단
    detect_macd_zero_cross: MACD 0선 교차 감지
    determine_stage: 현재 스테이지 판단 (메인 함수)
    detect_stage_transition: 스테이지 전환 시점 감지
    calculate_ma_spread: 이동평균선 간격 계산
    check_ma_slope: 이동평균선 기울기 확인
    get_stage_strategy: 스테이지별 권장 전략 제공
"""

import pandas as pd
import numpy as np
from typing import Union, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


def determine_ma_arrangement(data: pd.DataFrame) -> pd.Series:
    """
    이동평균선 배열 순서 판단
    
    3개 이동평균선(5일, 20일, 40일)의 상하 위치 관계를 판단하여
    6가지 배열 패턴 중 하나로 분류합니다.
    
    Args:
        data: DataFrame (EMA_5, EMA_20, EMA_40 컬럼 필요)
    
    Returns:
        pd.Series: 각 시점의 배열 상태 (1~6)
            1: 단기 > 중기 > 장기 (완전 정배열)
            2: 중기 > 단기 > 장기
            3: 중기 > 장기 > 단기
            4: 장기 > 중기 > 단기 (완전 역배열)
            5: 장기 > 단기 > 중기
            6: 단기 > 장기 > 중기
    
    Raises:
        ValueError: 필수 컬럼이 없을 경우
        TypeError: 잘못된 데이터 타입일 경우
    
    Examples:
        >>> df = pd.DataFrame({
        ...     'EMA_5': [110, 105, 100],
        ...     'EMA_20': [105, 100, 95],
        ...     'EMA_40': [100, 95, 90]
        ... })
        >>> arrangement = determine_ma_arrangement(df)
        >>> print(arrangement)
        0    1
        1    1
        2    1
        dtype: int64
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['EMA_5', 'EMA_20', 'EMA_40']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"이동평균선 배열 판단 시작: {len(data)}개 데이터")
    
    # 이동평균선 추출
    ema_5 = data['EMA_5']
    ema_20 = data['EMA_20']
    ema_40 = data['EMA_40']
    
    # 배열 판단 (초기값 0)
    arrangement = pd.Series(0, index=data.index, dtype=int)
    
    # 6가지 배열 패턴 판단
    # 패턴 1: 단기 > 중기 > 장기 (완전 정배열)
    arrangement[(ema_5 > ema_20) & (ema_20 > ema_40)] = 1
    
    # 패턴 2: 중기 > 단기 > 장기
    arrangement[(ema_20 > ema_5) & (ema_5 > ema_40)] = 2
    
    # 패턴 3: 중기 > 장기 > 단기
    arrangement[(ema_20 > ema_40) & (ema_40 > ema_5)] = 3
    
    # 패턴 4: 장기 > 중기 > 단기 (완전 역배열)
    arrangement[(ema_40 > ema_20) & (ema_20 > ema_5)] = 4
    
    # 패턴 5: 장기 > 단기 > 중기
    arrangement[(ema_40 > ema_5) & (ema_5 > ema_20)] = 5
    
    # 패턴 6: 단기 > 장기 > 중기
    arrangement[(ema_5 > ema_40) & (ema_40 > ema_20)] = 6
    
    # 0인 값 확인 (판단 불가능한 경우)
    undefined_count = (arrangement == 0).sum()
    if undefined_count > 0:
        logger.warning(f"배열 판단 불가: {undefined_count}개 (NaN 또는 동일값)")
    
    logger.debug(f"이동평균선 배열 판단 완료")
    
    return arrangement


def detect_macd_zero_cross(data: pd.DataFrame) -> pd.DataFrame:
    """
    MACD 0선 교차 감지
    
    3종 MACD(상, 중, 하)의 0선 교차 시점을 감지합니다.
    골든크로스(음수→양수)와 데드크로스(양수→음수)를 구분합니다.
    
    Args:
        data: DataFrame (MACD_상, MACD_중, MACD_하 컬럼 필요)
    
    Returns:
        pd.DataFrame: 3개 컬럼
            Cross_상: MACD(상) 0선 교차 (1: 골든크로스, -1: 데드크로스, 0: 없음)
            Cross_중: MACD(중) 0선 교차
            Cross_하: MACD(하) 0선 교차
    
    Raises:
        ValueError: 필수 컬럼이 없을 경우
        TypeError: 잘못된 데이터 타입일 경우
    
    Notes:
        - 골든크로스: 전일 음수 & 당일 양수 (MACD가 0선을 아래에서 위로 돌파)
        - 데드크로스: 전일 양수 & 당일 음수 (MACD가 0선을 위에서 아래로 돌파)
        - MACD 0선 교차 = 해당 이동평균선 교차
    
    MACD 교차와 스테이지 전환:
        - MACD(상) +→0: 제2스테이지 (데드크로스1)
        - MACD(중) +→0: 제3스테이지 (데드크로스2)
        - MACD(하) +→0: 제4스테이지 (데드크로스3)
        - MACD(상) -→0: 제5스테이지 (골든크로스1)
        - MACD(중) -→0: 제6스테이지 (골든크로스2)
        - MACD(하) -→0: 제1스테이지 (골든크로스3)
    
    Examples:
        >>> df = pd.DataFrame({
        ...     'MACD_상': [-1, -0.5, 0.5, 1, 0.5, -0.5],
        ...     'MACD_중': [1, 0.5, -0.5, -1, -0.5, 0.5],
        ...     'MACD_하': [0.5, 1, 0.5, -0.5, -1, -0.5]
        ... })
        >>> crosses = detect_macd_zero_cross(df)
        >>> print(crosses)
           Cross_상  Cross_중  Cross_하
        0        0        0        0
        1        0        0        0
        2        1       -1        0
        3        0        0       -1
        4        0        0        0
        5       -1        1        0
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['MACD_상', 'MACD_중', 'MACD_하']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"MACD 0선 교차 감지 시작: {len(data)}개 데이터")
    
    # 결과 DataFrame 생성
    crosses = pd.DataFrame(index=data.index)
    
    # 각 MACD에 대해 0선 교차 감지
    for macd_col in ['MACD_상', 'MACD_중', 'MACD_하']:
        macd = data[macd_col]
        
        # 골든크로스: 전일 음수 & 당일 양수
        golden_cross = (macd.shift(1) < 0) & (macd > 0)
        
        # 데드크로스: 전일 양수 & 당일 음수
        dead_cross = (macd.shift(1) > 0) & (macd < 0)
        
        # 결과: 1(골든크로스), -1(데드크로스), 0(없음)
        cross_name = macd_col.replace('MACD_', 'Cross_')
        crosses[cross_name] = golden_cross.astype(int) - dead_cross.astype(int)
    
    # 교차 발생 통계
    total_crosses = (crosses != 0).sum().sum()
    golden_crosses = (crosses == 1).sum().sum()
    dead_crosses = (crosses == -1).sum().sum()
    
    logger.debug(f"MACD 0선 교차 감지 완료: "
                f"총 {total_crosses}회 (골든 {golden_crosses}회, 데드 {dead_crosses}회)")
    
    return crosses


def determine_stage(data: pd.DataFrame) -> pd.Series:
    """
    이동평균선 배열과 MACD 0선 교차를 종합하여 현재 스테이지 판단
    
    6단계 스테이지 대순환 분석의 핵심 함수입니다.
    이동평균선 배열로 기본 스테이지를 판단하고,
    MACD 0선 교차로 스테이지 전환을 확정합니다.
    
    Args:
        data: DataFrame (모든 지표 포함)
              필수 컬럼: EMA_5, EMA_20, EMA_40, MACD_상, MACD_중, MACD_하
    
    Returns:
        pd.Series: 각 시점의 스테이지 (1~6)
            1: 안정 상승기 (완전 정배열)
            2: 하락 변화기1 (데드크로스1 발생)
            3: 하락 변화기2 (데드크로스2 발생)
            4: 안정 하락기 (완전 역배열)
            5: 상승 변화기1 (골든크로스1 발생)
            6: 상승 변화기2 (골든크로스2 발생)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
    
    Notes:
        스테이지 판단 우선순위:
        1. MACD 0선 교차 (최우선) - 스테이지 전환 확정
        2. 이동평균선 배열 (기본) - 기본 스테이지 판단
        
        MACD 교차 우선순위 (동시 발생 시):
        Cross_하 > Cross_중 > Cross_상
        
        스테이지 전환 매핑:
        - Cross_하 = 1 (골든크로스3) → 제1스테이지
        - Cross_상 = -1 (데드크로스1) → 제2스테이지
        - Cross_중 = -1 (데드크로스2) → 제3스테이지
        - Cross_하 = -1 (데드크로스3) → 제4스테이지
        - Cross_상 = 1 (골든크로스1) → 제5스테이지
        - Cross_중 = 1 (골든크로스2) → 제6스테이지
    
    Examples:
        >>> from src.data import get_stock_data
        >>> from src.analysis.technical import calculate_all_indicators
        >>> 
        >>> # 데이터 수집 및 지표 계산
        >>> df = get_stock_data('005930', days=100)
        >>> df = calculate_all_indicators(df)
        >>> 
        >>> # 스테이지 판단
        >>> df['Stage'] = determine_stage(df)
        >>> 
        >>> # 현재 스테이지 확인
        >>> current_stage = df['Stage'].iloc[-1]
        >>> print(f"현재 스테이지: {current_stage}")
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['EMA_5', 'EMA_20', 'EMA_40', 'MACD_상', 'MACD_중', 'MACD_하']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"스테이지 판단 시작: {len(data)}개 데이터")
    
    # 1단계: 이동평균선 배열로 기본 스테이지 판단
    stage = determine_ma_arrangement(data)
    logger.debug("1단계: 이동평균선 배열 기반 스테이지 판단 완료")
    
    # 2단계: MACD 0선 교차 감지
    crosses = detect_macd_zero_cross(data)
    logger.debug("2단계: MACD 0선 교차 감지 완료")
    
    # 3단계: MACD 교차로 스테이지 확정 (우선순위: 하 > 중 > 상)
    # MACD(하) 골든크로스 → 제1스테이지 확정
    stage[crosses['Cross_하'] == 1] = 1
    gc3_count = (crosses['Cross_하'] == 1).sum()
    if gc3_count > 0:
        logger.info(f"골든크로스3 발생: {gc3_count}회 → 제1스테이지 확정")
    
    # MACD(하) 데드크로스 → 제4스테이지 확정
    stage[crosses['Cross_하'] == -1] = 4
    dc3_count = (crosses['Cross_하'] == -1).sum()
    if dc3_count > 0:
        logger.info(f"데드크로스3 발생: {dc3_count}회 → 제4스테이지 확정")
    
    # MACD(중) 골든크로스 → 제6스테이지 확정
    stage[crosses['Cross_중'] == 1] = 6
    gc2_count = (crosses['Cross_중'] == 1).sum()
    if gc2_count > 0:
        logger.info(f"골든크로스2 발생: {gc2_count}회 → 제6스테이지 확정")
    
    # MACD(중) 데드크로스 → 제3스테이지 확정
    stage[crosses['Cross_중'] == -1] = 3
    dc2_count = (crosses['Cross_중'] == -1).sum()
    if dc2_count > 0:
        logger.info(f"데드크로스2 발생: {dc2_count}회 → 제3스테이지 확정")
    
    # MACD(상) 골든크로스 → 제5스테이지 확정
    stage[crosses['Cross_상'] == 1] = 5
    gc1_count = (crosses['Cross_상'] == 1).sum()
    if gc1_count > 0:
        logger.info(f"골든크로스1 발생: {gc1_count}회 → 제5스테이지 확정")
    
    # MACD(상) 데드크로스 → 제2스테이지 확정
    stage[crosses['Cross_상'] == -1] = 2
    dc1_count = (crosses['Cross_상'] == -1).sum()
    if dc1_count > 0:
        logger.info(f"데드크로스1 발생: {dc1_count}회 → 제2스테이지 확정")
    
    # 스테이지 분포 로깅
    stage_counts = stage.value_counts().sort_index()
    logger.debug(f"스테이지 분포: {stage_counts.to_dict()}")
    
    logger.debug("3단계: MACD 교차 기반 스테이지 확정 완료")
    logger.info(f"스테이지 판단 완료: 총 {len(stage)}개")
    
    return stage


def detect_stage_transition(data: pd.DataFrame) -> pd.Series:
    """
    스테이지 전환 시점 감지
    
    이전 스테이지와 현재 스테이지를 비교하여 전환 발생 여부와
    전환 유형을 판단합니다.
    
    Args:
        data: DataFrame (Stage 컬럼 필요)
    
    Returns:
        pd.Series: 스테이지 전환 정보
            0: 전환 없음
            12: 제1→제2 전환 (데드크로스1)
            23: 제2→제3 전환 (데드크로스2)
            34: 제3→제4 전환 (데드크로스3)
            45: 제4→제5 전환 (골든크로스1)
            56: 제5→제6 전환 (골든크로스2)
            61: 제6→제1 전환 (골든크로스3, 순환 완료)
            기타: 비순차 전환 (예: 13, 24 등)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: Stage 컬럼이 없을 때
    
    Notes:
        전환 값 인코딩: 이전 스테이지 * 10 + 현재 스테이지
        
        정상 순차 전환:
        - 12, 23, 34, 45, 56, 61 (순환)
        
        비순차 전환 (급격한 변화):
        - 13, 24, 35 등 (드물지만 가능)
        
        첫 번째 데이터는 이전 비교 대상이 없으므로 0 반환
    
    Examples:
        >>> df = pd.DataFrame({
        ...     'Stage': [1, 1, 2, 2, 3, 3]
        ... })
        >>> transition = detect_stage_transition(df)
        >>> print(transition)
        0     0
        1     0
        2    12
        3     0
        4    23
        5     0
        dtype: int64
        
        >>> # 전환 발생 지점만 추출
        >>> transitions = df[transition != 0]
        >>> print(transitions)
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if 'Stage' not in data.columns:
        raise ValueError("Stage 컬럼이 필요합니다")
    
    logger.debug(f"스테이지 전환 감지 시작: {len(data)}개 데이터")
    
    # 현재 및 이전 스테이지
    current_stage = data['Stage']
    prev_stage = current_stage.shift(1)
    
    # 전환 여부 확인
    is_transition = (current_stage != prev_stage)
    
    # 전환 값 계산: 이전*10 + 현재
    transition = prev_stage * 10 + current_stage
    
    # 전환 없으면 0
    transition[~is_transition] = 0
    
    # 첫 행은 비교 불가 → 0
    transition.iloc[0] = 0
    
    # NaN 처리 (Stage가 NaN이면 transition도 NaN)
    transition[current_stage.isna()] = np.nan
    
    # 전환 발생 통계
    transition_count = (transition != 0).sum()
    if transition_count > 0:
        logger.info(f"스테이지 전환 발생: 총 {transition_count}회")
        
        # 전환 유형별 집계
        transition_types = transition[transition != 0].value_counts().sort_index()
        for trans_value, count in transition_types.items():
            if not np.isnan(trans_value):
                prev = int(trans_value / 10)
                curr = int(trans_value % 10)
                logger.debug(f"  제{prev}→제{curr} 전환: {count}회")
    else:
        logger.debug("스테이지 전환 없음")
    
    logger.debug("스테이지 전환 감지 완료")
    
    return transition.astype('Int64')  # nullable integer


def calculate_ma_spread(data: pd.DataFrame) -> pd.DataFrame:
    """
    이동평균선 간격 계산
    
    3개 이동평균선(5일, 20일, 40일) 간의 간격을 계산합니다.
    간격의 크기와 방향(양수/음수)으로 추세 강도와 배열 상태를 파악할 수 있습니다.
    
    Args:
        data: DataFrame (EMA_5, EMA_20, EMA_40 컬럼 필요)
    
    Returns:
        pd.DataFrame: 3개 컬럼
            Spread_5_20: 단기-중기 간격 (EMA_5 - EMA_20)
            Spread_20_40: 중기-장기 간격 (EMA_20 - EMA_40)
            Spread_5_40: 단기-장기 간격 (EMA_5 - EMA_40)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
    
    Examples:
        >>> df = pd.DataFrame({
        ...     'EMA_5': [110, 115, 120],
        ...     'EMA_20': [105, 108, 112],
        ...     'EMA_40': [100, 102, 105]
        ... })
        >>> spreads = calculate_ma_spread(df)
        >>> print(spreads['Spread_5_20'])
        0    5
        1    7
        2    8
        dtype: float64
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['EMA_5', 'EMA_20', 'EMA_40']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"이동평균선 간격 계산 시작: {len(data)}개 데이터")
    
    # 간격 계산 (단순 뺄셈)
    spreads = pd.DataFrame(index=data.index)
    
    spreads['Spread_5_20'] = data['EMA_5'] - data['EMA_20']
    spreads['Spread_20_40'] = data['EMA_20'] - data['EMA_40']
    spreads['Spread_5_40'] = data['EMA_5'] - data['EMA_40']
    
    # 통계 로깅
    logger.debug(f"Spread_5_20 평균: {spreads['Spread_5_20'].mean():.2f}")
    logger.debug(f"Spread_20_40 평균: {spreads['Spread_20_40'].mean():.2f}")
    logger.debug(f"Spread_5_40 평균: {spreads['Spread_5_40'].mean():.2f}")
    
    logger.debug("이동평균선 간격 계산 완료")
    
    return spreads


def check_ma_slope(data: pd.DataFrame, period: int = 5) -> pd.DataFrame:
    """
    이동평균선 기울기 확인
    
    3개 이동평균선(5일, 20일, 40일)의 기울기를 계산합니다.
    기울기를 통해 각 이동평균선의 방향성(우상향/평행/우하향)을 판단할 수 있습니다.
    
    Args:
        data: DataFrame (EMA_5, EMA_20, EMA_40 컬럼 필요)
        period: 기울기 계산 기간 (기본값: 5)
    
    Returns:
        pd.DataFrame: 3개 컬럼
            Slope_EMA_5: 단기선 기울기
            Slope_EMA_20: 중기선 기울기
            Slope_EMA_40: 장기선 기울기
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼 없거나 period가 2 미만일 때
    
    Notes:
        - Level 2의 calculate_slope() 함수를 재사용합니다
        - 기울기 > 0: 우상향 (상승 추세)
        - 기울기 ≈ 0: 평행 (추세 전환 임박)
        - 기울기 < 0: 우하향 (하락 추세)
    
    Examples:
        >>> df = pd.DataFrame({
        ...     'EMA_5': [100, 102, 105, 109, 114],
        ...     'EMA_20': [95, 97, 99, 102, 105],
        ...     'EMA_40': [90, 91, 93, 95, 97]
        ... })
        >>> slopes = check_ma_slope(df, period=3)
        >>> print(slopes['Slope_EMA_5'].iloc[-1] > 0)
        True
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['EMA_5', 'EMA_20', 'EMA_40']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    if period < 2:
        raise ValueError(f"period는 2 이상이어야 합니다. 입력값: {period}")
    
    logger.debug(f"이동평균선 기울기 계산 시작: {len(data)}개, period={period}")
    
    # 각 이동평균선의 기울기 계산
    slopes = pd.DataFrame(index=data.index)
    
    # Level 2에서 구현한 calculate_slope 재사용
    from src.analysis.technical.indicators import calculate_slope
    
    slopes['Slope_EMA_5'] = calculate_slope(data['EMA_5'], period=period)
    slopes['Slope_EMA_20'] = calculate_slope(data['EMA_20'], period=period)
    slopes['Slope_EMA_40'] = calculate_slope(data['EMA_40'], period=period)
    
    # 기울기 통계
    for col in ['Slope_EMA_5', 'Slope_EMA_20', 'Slope_EMA_40']:
        slope_mean = slopes[col].mean()
        slope_std = slopes[col].std()
        logger.debug(f"{col}: 평균={slope_mean:.4f}, 표준편차={slope_std:.4f}")
    
    logger.debug("이동평균선 기울기 계산 완료")
    
    return slopes


def get_stage_strategy(
    stage: int,
    macd_directions: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    스테이지별 권장 전략 제공
    
    각 스테이지에 맞는 구체적인 매매 전략과 액션을 제공합니다.
    MACD 방향 정보를 추가로 제공하면 신호 강도를 함께 분석합니다.
    
    Args:
        stage: 현재 스테이지 (1~6)
        macd_directions: 3개 MACD 방향 (선택)
            예: {'상': 'up', '중': 'up', '하': 'up'}
    
    Returns:
        Dict: 전략 정보
            - stage: 스테이지 번호 (int)
            - name: 스테이지 이름 (str)
            - market_phase: 시장 국면 (str)
            - strategy: 권장 전략 (str)
            - action: 구체적 액션 (str)
            - position_size: 포지션 크기 (str)
            - risk_level: 리스크 레벨 (str)
            - description: 상세 설명 (str)
            - key_points: 핵심 포인트 리스트 (List[str])
            - macd_directions: MACD 방향 정보 (Dict, 선택)
            - macd_alignment: MACD 일치도 (Dict, 선택)
    
    Raises:
        TypeError: stage가 정수가 아닐 때
        ValueError: stage가 1~6 범위 밖일 때
    
    Examples:
        >>> strategy = get_stage_strategy(1)
        >>> print(strategy['name'])
        안정 상승기
        >>> print(strategy['action'])
        buy
        
        >>> # MACD 방향 포함
        >>> macd_dirs = {'상': 'up', '중': 'up', '하': 'up'}
        >>> strategy = get_stage_strategy(1, macd_directions=macd_dirs)
        >>> print(strategy['macd_alignment']['strength'])
        strong
    """
    # 입력 검증
    if not isinstance(stage, (int, np.integer)):
        raise TypeError(f"stage는 정수여야 합니다. 입력 타입: {type(stage)}")
    
    if stage < 1 or stage > 6:
        raise ValueError(f"stage는 1~6 사이여야 합니다. 입력값: {stage}")
    
    logger.debug(f"스테이지 {stage} 전략 조회")
    
    # 스테이지별 전략 매핑 (딕셔너리)
    strategies = {
        1: {
            'stage': 1,
            'name': '안정 상승기',
            'market_phase': '강세장',
            'strategy': '공격적 매수',
            'action': 'buy',
            'position_size': '적극적 (80-100%)',
            'risk_level': 'low',
            'description': '완전 정배열, 강한 상승 추세. 매수 포지션 확대 최적기',
            'key_points': [
                '3개 이동평균선 모두 우상향',
                '이동평균선 간격 확대 중',
                '매수 포지션 확대 적기',
                'MACD(하) 골든크로스로 상승 확정',
                '추세 지속 기대'
            ]
        },
        2: {
            'stage': 2,
            'name': '하락 변화기1',
            'market_phase': '약세 전환 초기',
            'strategy': '포지션 유지 판단',
            'action': 'hold_or_exit',
            'position_size': '유지 또는 축소 (50-80%)',
            'risk_level': 'medium',
            'description': 'MACD(상) 데드크로스 발생. 단기선이 중기선 아래로 하락',
            'key_points': [
                '단기선이 중기선 아래로 하락',
                'MACD(상) 데드크로스 (주의 신호)',
                '중기-장기 간격 확인 필요',
                '장기선이 여전히 상승 중이면 유지',
                '장기선이 꺾이면 청산 검토'
            ]
        },
        3: {
            'stage': 3,
            'name': '하락 변화기2',
            'market_phase': '약세 가속',
            'strategy': '매수 청산, 매도 진입',
            'action': 'sell_or_short',
            'position_size': '전량 청산 또는 매도 진입',
            'risk_level': 'high',
            'description': 'MACD(중) 데드크로스. 단기선이 장기선 아래로 하락',
            'key_points': [
                '단기선이 장기선 아래로 하락',
                'MACD(중) 데드크로스 (강한 하락 신호)',
                '매수 포지션 전량 청산',
                '공격적 투자자는 매도 진입 고려',
                '하락 추세 시작'
            ]
        },
        4: {
            'stage': 4,
            'name': '안정 하락기',
            'market_phase': '약세장',
            'strategy': '공격적 매도 (또는 관망)',
            'action': 'short_or_wait',
            'position_size': '적극적 매도 (또는 현금 보유)',
            'risk_level': 'low',
            'description': '완전 역배열, 강한 하락 추세. 매도 포지션 확대 적기',
            'key_points': [
                '3개 이동평균선 모두 우하향',
                '이동평균선 간격 확대 중 (역방향)',
                '매도 포지션 확대 적기 (공격적 투자자)',
                'MACD(하) 데드크로스로 하락 확정',
                '보수적 투자자는 현금 보유 관망'
            ]
        },
        5: {
            'stage': 5,
            'name': '상승 변화기1',
            'market_phase': '강세 전환 초기',
            'strategy': '포지션 유지 판단',
            'action': 'hold_or_exit',
            'position_size': '유지 또는 축소 (50-80%)',
            'risk_level': 'medium',
            'description': 'MACD(상) 골든크로스 발생. 단기선이 중기선 위로 상승',
            'key_points': [
                '단기선이 중기선 위로 상승',
                'MACD(상) 골든크로스 (긍정 신호)',
                '중기-장기 간격 확인 필요',
                '장기선이 여전히 하락 중이면 유지',
                '장기선이 반등하면 청산 검토'
            ]
        },
        6: {
            'stage': 6,
            'name': '상승 변화기2',
            'market_phase': '강세 가속',
            'strategy': '매도 청산, 매수 진입',
            'action': 'cover_or_buy',
            'position_size': '전량 청산 또는 매수 진입',
            'risk_level': 'high',
            'description': 'MACD(중) 골든크로스. 단기선이 장기선 위로 상승',
            'key_points': [
                '단기선이 장기선 위로 상승',
                'MACD(중) 골든크로스 (강한 상승 신호)',
                '매도 포지션 전량 청산',
                '조기 매수 진입 고려',
                '상승 추세 시작 임박'
            ]
        }
    }
    
    # 해당 스테이지 전략 가져오기
    strategy = strategies[stage].copy()
    
    # MACD 방향 정보 추가 (선택)
    if macd_directions is not None:
        strategy['macd_directions'] = macd_directions
        
        # MACD 방향 일치도 계산
        up_count = sum(1 for d in macd_directions.values() if d == 'up')
        down_count = sum(1 for d in macd_directions.values() if d == 'down')
        neutral_count = sum(1 for d in macd_directions.values() if d == 'neutral')
        
        strategy['macd_alignment'] = {
            'up_count': up_count,
            'down_count': down_count,
            'neutral_count': neutral_count,
            'strength': 'strong' if (up_count == 3 or down_count == 3) else 'weak'
        }
        
        logger.debug(f"MACD 방향: 상승={up_count}, 하락={down_count}, 중립={neutral_count}")
    
    logger.debug(f"전략 조회 완료: {strategy['name']}")
    
    return strategy
