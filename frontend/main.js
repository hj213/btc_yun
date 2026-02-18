const analyzeBtn = document.getElementById('analyzeBtn');
const resultContainer = document.getElementById('resultContainer');
const priceValue = document.getElementById('priceValue');
const scoreValue = document.getElementById('scoreValue');
const timeValue = document.getElementById('timeValue');
const chartImg = document.getElementById('chartImg');
const btnText = analyzeBtn.querySelector('.btn-text');
const loader = analyzeBtn.querySelector('.loader');

analyzeBtn.addEventListener('click', async () => {
    try {
        // UI 상태 업데이트: 로딩 중
        analyzeBtn.disabled = true;
        btnText.textContent = '분석 중...';
        loader.classList.remove('hidden');

        // 백엔드 API 호출 (Vite/배포 환경 통합을 위해 상대 경로 사용)
        const response = await fetch('/api/analyze');
        const data = await response.json();

        if (data.status === 'success') {
            // 데이터 표기
            priceValue.textContent = new Intl.NumberFormat('en-US').format(data.price);
            scoreValue.textContent = data.score.toFixed(1);
            timeValue.textContent = data.time;
            chartImg.src = data.chart;

            // 결과창 표시 및 스크롤
            resultContainer.classList.remove('hidden');
            resultContainer.scrollIntoView({ behavior: 'smooth' });

            // 점수에 따른 강조 색상 변경 (예시)
            if (data.score >= 2) {
                scoreValue.style.color = '#f43f5e'; // Strong (Red)
            } else if (data.score <= 1) {
                scoreValue.style.color = '#10b981'; // Weak (Green)
            } else {
                scoreValue.style.color = '#38bdf8'; // Normal (Blue)
            }
        } else {
            alert('에러 발생: ' + data.message);
        }
    } catch (error) {
        console.error('Fetch Error:', error);
        alert('백엔드 서버가 실행 중인지 확인해주세요.');
    } finally {
        // UI 상태 복구
        analyzeBtn.disabled = false;
        btnText.textContent = '분석 시작하기';
        loader.classList.add('hidden');
    }
});
