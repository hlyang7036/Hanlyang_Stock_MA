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
from typing import Union, Dict, Optional
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
