const analyzeBtn = document.getElementById('analyzeBtn');
const resultWrapper = document.getElementById('resultWrapper');
const resultTemplate = document.getElementById('resultTemplate');
const lastUpdate = document.getElementById('lastUpdate');
const timeValue = document.getElementById('timeValue');
const btnText = analyzeBtn.querySelector('.btn-text');
const loader = analyzeBtn.querySelector('.loader');

analyzeBtn.addEventListener('click', async () => {
    try {
        // UI 상태 업데이트: 로딩 중
        analyzeBtn.disabled = true;
        btnText.textContent = '전체 분석 중...';
        loader.classList.remove('hidden');
        resultWrapper.innerHTML = ''; // 이전 결과 초기화
        lastUpdate.classList.add('hidden');

        // 백엔드 API 호출
        const response = await fetch('/api/analyze');
        const data = await response.json();

        if (data.status === 'success') {
            // 시간 표기
            timeValue.textContent = data.time;
            lastUpdate.classList.remove('hidden');

            // 개별 결과 렌더링
            data.results.forEach(result => {
                if (result.error) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'glass';
                    errorDiv.style.padding = '1rem';
                    errorDiv.style.color = '#f43f5e';
                    errorDiv.textContent = `${result.name} 분석 에러: ${result.error}`;
                    resultWrapper.appendChild(errorDiv);
                    return;
                }

                const clone = resultTemplate.content.cloneNode(true);

                clone.querySelector('.result-title').textContent = result.name;
                clone.querySelector('.price-value').textContent = new Intl.NumberFormat('en-US').format(result.price);
                clone.querySelector('.price-unit').textContent = result.unit;

                const scoreEl = clone.querySelector('.score-value');
                scoreEl.textContent = result.score.toFixed(0);

                // 점수에 따른 색상 (BTC는 3점이 만점, 주식은 3점이 만점/초과 가능)
                if (result.score >= 2) {
                    scoreEl.style.color = '#f43f5e';
                } else if (result.score <= 1) {
                    scoreEl.style.color = '#10b981';
                } else {
                    scoreEl.style.color = '#38bdf8';
                }

                clone.querySelector('.chart-img').src = result.chart;
                clone.querySelector('.chart-img').alt = `${result.name} 분석 차트`;

                resultWrapper.appendChild(clone);
            });

            // 상단으로 스크롤
            resultWrapper.scrollIntoView({ behavior: 'smooth' });
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
