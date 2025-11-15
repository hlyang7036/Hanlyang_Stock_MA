"""
신호 필터링 모듈

이 모듈은 생성된 매매 신호를 필터링하여 품질이 낮거나 위험한 신호를 제거합니다.

Functions:
    apply_signal_filters: 종합 필터링 적용
    check_strength_filter: 신호 강도 필터
    check_volatility_filter: 변동성 필터 (과도한 변동성 제외)
    check_trend_filter: 추세 필터 (약한 추세 제외)
    check_conflicting_signals: 상충 신호 체크
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


def check_strength_filter(
    data: pd.DataFrame,
    min_strength: int = 50
) -> pd.Series:
    """
    신호 강도 필터
    
    신호 강도가 최소 임계값 이상인 신호만 통과시킵니다.
    품질이 낮은 신호를 제거하여 승률을 높이는 것이 목적입니다.
    
    Args:
        data: DataFrame (Signal_Strength 컬럼 필요)
        min_strength: 최소 신호 강도 (0-100, 기본값: 50)
    
    Returns:
        pd.Series: 필터 통과 여부 (boolean)
            - True: 필터 통과 (min_strength 이상)
            - False: 필터 미통과 (min_strength 미만)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없거나 min_strength가 범위 밖일 때
    
    Examples:
        >>> df['Strength_Pass'] = check_strength_filter(df, min_strength=60)
        >>> strong_signals = df[df['Strength_Pass']]
    
    Notes:
        - 기본값 50점: 보통 이상의 신호만 통과
        - 높은 값(70-80): 강한 신호만 선택 (승률 ↑, 빈도 ↓)
        - 낮은 값(30-40): 더 많은 신호 허용 (승률 ↓, 빈도 ↑)
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if 'Signal_Strength' not in data.columns:
        raise ValueError("Signal_Strength 컬럼이 필요합니다")
    
    if not (0 <= min_strength <= 100):
        raise ValueError(f"min_strength는 0-100 범위여야 합니다: {min_strength}")
    
    logger.debug(f"신호 강도 필터 적용: 최소 {min_strength}점")
    
    # 필터 적용
    passed = data['Signal_Strength'] >= min_strength
    
    # 통계 로깅
    pass_count = passed.sum()
    if len(data) > 0:
        pass_rate = pass_count / len(data) * 100
        logger.info(f"강도 필터 통과: {pass_count}/{len(data)}개 ({pass_rate:.1f}%)")
    
    return passed


def check_volatility_filter(
    data: pd.DataFrame,
    max_atr_percentile: float = 90
) -> pd.Series:
    """
    변동성 필터 (과도한 변동성 제외)
    
    ATR이 너무 높은 경우 위험도가 크므로 신호를 제외합니다.
    적정 변동성 범위 내의 신호만 통과시킵니다.
    
    Args:
        data: DataFrame (ATR 컬럼 필요)
        max_atr_percentile: ATR 최대 백분위수 (0-100, 기본값: 90)
    
    Returns:
        pd.Series: 필터 통과 여부 (boolean)
            - True: 필터 통과 (ATR이 백분위수 이하)
            - False: 필터 미통과 (ATR이 너무 높음)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없거나 max_atr_percentile이 범위 밖일 때
    
    Examples:
        >>> df['Volatility_Pass'] = check_volatility_filter(df, max_atr_percentile=85)
        >>> safe_signals = df[df['Volatility_Pass']]
    
    Notes:
        - 기본값 90%: 상위 10% 고변동성 제외
        - 높은 값(95%): 극단적 변동성만 제외
        - 낮은 값(80%): 변동성이 큰 신호 적극 제거
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if 'ATR' not in data.columns:
        raise ValueError("ATR 컬럼이 필요합니다")
    
    if not (0 <= max_atr_percentile <= 100):
        raise ValueError(f"max_atr_percentile은 0-100 범위여야 합니다: {max_atr_percentile}")
    
    logger.debug(f"변동성 필터 적용: 최대 {max_atr_percentile}% 백분위")
    
    # ATR 백분위수 계산
    atr_percentile = data['ATR'].rank(pct=True) * 100
    
    # 최대 백분위수 이하만 통과
    passed = atr_percentile <= max_atr_percentile
    
    # 통계 로깅
    pass_count = passed.sum()
    if len(data) > 0:
        pass_rate = pass_count / len(data) * 100
        atr_threshold = data['ATR'].quantile(max_atr_percentile / 100)
        logger.info(f"변동성 필터 통과: {pass_count}/{len(data)}개 ({pass_rate:.1f}%)")
        logger.info(f"ATR 임계값: {atr_threshold:.4f}")
    
    return passed


def check_trend_filter(
    data: pd.DataFrame,
    min_slope: float = 0.1
) -> pd.Series:
    """
    추세 필터 (약한 추세 제외)
    
    장기선(EMA_40) 기울기가 너무 작으면 명확한 추세가 아니므로 신호를 제외합니다.
    강한 추세 환경에서만 진입하여 성공 확률을 높입니다.
    
    Args:
        data: DataFrame (Slope_EMA_40 컬럼 필요)
        min_slope: 최소 기울기 절댓값 (기본값: 0.1)
    
    Returns:
        pd.Series: 필터 통과 여부 (boolean)
            - True: 필터 통과 (기울기가 충분히 큼)
            - False: 필터 미통과 (횡보 또는 약한 추세)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없거나 min_slope가 음수일 때
    
    Examples:
        >>> df['Trend_Pass'] = check_trend_filter(df, min_slope=0.15)
        >>> strong_trend_signals = df[df['Trend_Pass']]
    
    Notes:
        - 기본값 0.1: 약한 추세 제외
        - 높은 값(0.2-0.3): 강한 추세만 선택
        - 낮은 값(0.05): 완만한 추세도 허용
        - 상승/하락 구분 없이 절댓값 평가
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if 'Slope_EMA_40' not in data.columns:
        raise ValueError("Slope_EMA_40 컬럼이 필요합니다")
    
    if min_slope < 0:
        raise ValueError(f"min_slope는 0 이상이어야 합니다: {min_slope}")
    
    logger.debug(f"추세 필터 적용: 최소 기울기 {min_slope:.3f}")
    
    # 기울기 절댓값이 최소값 이상인 경우만 통과
    passed = data['Slope_EMA_40'].abs() >= min_slope
    
    # 통계 로깅
    pass_count = passed.sum()
    if len(data) > 0:
        pass_rate = pass_count / len(data) * 100
        avg_slope = data.loc[passed, 'Slope_EMA_40'].abs().mean() if pass_count > 0 else 0
        logger.info(f"추세 필터 통과: {pass_count}/{len(data)}개 ({pass_rate:.1f}%)")
        logger.info(f"평균 기울기 (통과): {avg_slope:.4f}")
    
    return passed


def check_conflicting_signals(data: pd.DataFrame) -> pd.Series:
    """
    상충 신호 체크
    
    진입 신호와 청산 신호가 동시에 발생하는 경우를 감지합니다.
    상충되는 신호는 신뢰도가 낮으므로 제외합니다.
    
    Args:
        data: DataFrame (Entry_Signal, Exit_Signal 컬럼 필요)
    
    Returns:
        pd.Series: 신호 상충 여부 (boolean)
            - True: 상충 없음 (정상 신호)
            - False: 상충 발생 (진입과 청산 동시)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
    
    Examples:
        >>> df['No_Conflict'] = check_conflicting_signals(df)
        >>> clean_signals = df[df['No_Conflict']]
    
    Notes:
        - Entry_Signal != 0: 진입 신호 있음
        - Exit_Signal != 0: 청산 신호 있음
        - 둘 다 0이 아닌 경우: 상충 (제외)
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    # 컬럼 존재 여부 확인 (둘 다 없어도 통과 - 선택적 필터)
    has_entry = 'Entry_Signal' in data.columns
    has_exit = 'Exit_Signal' in data.columns
    
    if not has_entry and not has_exit:
        # 둘 다 없으면 상충 체크 불가 - 모두 통과
        logger.debug("Entry_Signal, Exit_Signal 컬럼 없음. 상충 체크 건너뜀")
        return pd.Series(True, index=data.index)
    
    logger.debug("상충 신호 체크 중...")
    
    # 진입 신호 여부
    has_entry_signal = pd.Series(False, index=data.index)
    if has_entry:
        has_entry_signal = data['Entry_Signal'] != 0
    
    # 청산 신호 여부
    has_exit_signal = pd.Series(False, index=data.index)
    if has_exit:
        has_exit_signal = data['Exit_Signal'] != 0
    
    # 상충 감지: 진입과 청산이 동시에 발생
    conflicting = has_entry_signal & has_exit_signal
    
    # 상충 없는 경우만 통과
    passed = ~conflicting
    
    # 통계 로깅
    conflict_count = conflicting.sum()
    if len(data) > 0:
        conflict_rate = conflict_count / len(data) * 100
        logger.info(f"상충 신호: {conflict_count}개 ({conflict_rate:.1f}%)")
        if conflict_count > 0:
            logger.warning(f"진입-청산 동시 발생 신호 {conflict_count}개 제외됨")
    
    return passed


def apply_signal_filters(
    data: pd.DataFrame,
    min_strength: int = 50,
    enable_filters: Optional[Dict[str, bool]] = None
) -> pd.DataFrame:
    """
    신호 필터링 적용
    
    여러 필터를 조합하여 신호를 필터링합니다.
    각 필터는 선택적으로 활성화/비활성화할 수 있습니다.
    
    Args:
        data: DataFrame (신호 및 지표 데이터)
        min_strength: 최소 신호 강도 (0-100, 기본값: 50)
        enable_filters: 필터 활성화 설정 (기본값: 모든 필터 활성화)
            예: {
                'strength': True,
                'volatility': True,
                'trend': True,
                'conflict': True
            }
    
    Returns:
        pd.DataFrame: 필터링된 신호 (원본 DataFrame + 추가 컬럼)
            - Filter_Strength: 강도 필터 통과 여부
            - Filter_Volatility: 변동성 필터 통과 여부
            - Filter_Trend: 추세 필터 통과 여부
            - Filter_Conflict: 상충 필터 통과 여부
            - Filter_Passed: 모든 활성 필터 통과 여부
            - Filter_Reasons: 필터링 이유 (통과 실패 시)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
    
    Examples:
        >>> # 모든 필터 사용
        >>> filtered = apply_signal_filters(df, min_strength=60)
        >>> 
        >>> # 선택적 필터 사용
        >>> filtered = apply_signal_filters(
        ...     df,
        ...     min_strength=50,
        ...     enable_filters={'strength': True, 'volatility': True, 'trend': False}
        ... )
        >>> 
        >>> # 통과한 신호만 선택
        >>> passed_signals = filtered[filtered['Filter_Passed']]
    
    Notes:
        - 모든 활성 필터를 통과해야 최종 통과
        - 비활성 필터는 자동으로 통과 처리
        - Filter_Reasons는 실패한 필터 목록 제공
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    logger.info(f"신호 필터링 시작: {len(data)}개 신호")
    
    # 기본 필터 설정
    if enable_filters is None:
        enable_filters = {
            'strength': True,
            'volatility': True,
            'trend': True,
            'conflict': True
        }
    
    # 결과 DataFrame 복사
    result = data.copy()
    
    # 각 필터 결과 저장
    filter_results = {}
    
    # 1. 강도 필터
    if enable_filters.get('strength', True):
        try:
            filter_results['strength'] = check_strength_filter(data, min_strength)
            logger.debug(f"강도 필터 적용 완료")
        except Exception as e:
            logger.warning(f"강도 필터 실패 (모두 통과 처리): {e}")
            filter_results['strength'] = pd.Series(True, index=data.index)
    else:
        logger.debug("강도 필터 비활성화")
        filter_results['strength'] = pd.Series(True, index=data.index)
    
    # 2. 변동성 필터
    if enable_filters.get('volatility', True):
        try:
            filter_results['volatility'] = check_volatility_filter(data)
            logger.debug(f"변동성 필터 적용 완료")
        except Exception as e:
            logger.warning(f"변동성 필터 실패 (모두 통과 처리): {e}")
            filter_results['volatility'] = pd.Series(True, index=data.index)
    else:
        logger.debug("변동성 필터 비활성화")
        filter_results['volatility'] = pd.Series(True, index=data.index)
    
    # 3. 추세 필터
    if enable_filters.get('trend', True):
        try:
            filter_results['trend'] = check_trend_filter(data)
            logger.debug(f"추세 필터 적용 완료")
        except Exception as e:
            logger.warning(f"추세 필터 실패 (모두 통과 처리): {e}")
            filter_results['trend'] = pd.Series(True, index=data.index)
    else:
        logger.debug("추세 필터 비활성화")
        filter_results['trend'] = pd.Series(True, index=data.index)
    
    # 4. 상충 신호 필터
    if enable_filters.get('conflict', True):
        try:
            filter_results['conflict'] = check_conflicting_signals(data)
            logger.debug(f"상충 필터 적용 완료")
        except Exception as e:
            logger.warning(f"상충 필터 실패 (모두 통과 처리): {e}")
            filter_results['conflict'] = pd.Series(True, index=data.index)
    else:
        logger.debug("상충 필터 비활성화")
        filter_results['conflict'] = pd.Series(True, index=data.index)
    
    # 결과 컬럼 추가
    result['Filter_Strength'] = filter_results['strength']
    result['Filter_Volatility'] = filter_results['volatility']
    result['Filter_Trend'] = filter_results['trend']
    result['Filter_Conflict'] = filter_results['conflict']
    
    # 전체 필터 통과 여부 (모든 활성 필터를 통과해야 함)
    result['Filter_Passed'] = (
        filter_results['strength'] &
        filter_results['volatility'] &
        filter_results['trend'] &
        filter_results['conflict']
    )
    
    # 필터링 이유 생성
    def get_filter_reasons(row):
        reasons = []
        if not row['Filter_Strength']:
            reasons.append('강도 부족')
        if not row['Filter_Volatility']:
            reasons.append('고변동성')
        if not row['Filter_Trend']:
            reasons.append('약한 추세')
        if not row['Filter_Conflict']:
            reasons.append('신호 상충')
        return ', '.join(reasons) if reasons else ''
    
    result['Filter_Reasons'] = result.apply(get_filter_reasons, axis=1)
    
    # 통계 로깅
    passed_count = result['Filter_Passed'].sum()
    if len(result) > 0:
        pass_rate = passed_count / len(result) * 100
        logger.info(f"필터링 완료: {passed_count}/{len(result)}개 통과 ({pass_rate:.1f}%)")
        
        # 각 필터별 통과율
        logger.info(f"  - 강도: {filter_results['strength'].sum()}개")
        logger.info(f"  - 변동성: {filter_results['volatility'].sum()}개")
        logger.info(f"  - 추세: {filter_results['trend'].sum()}개")
        logger.info(f"  - 상충: {filter_results['conflict'].sum()}개")
    
    return result
