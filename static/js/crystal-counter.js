function initCrystalCounter() {
    var canvas = document.getElementById('crystal-counter');
    if (!canvas) return;
    
    canvas.width = 200;
    canvas.height = 200;
    var ctx = canvas.getContext('2d');
    
    var isNight = false;
    var count = 0;
    var rotation = 0;
    var isHovering = false;
    var floatOffset = 0;

    function drawNum(n) {
        ctx.clearRect(0, 0, 200, 200);
        var color = isNight ? '#ffaa44' : '#88ccff';
        ctx.fillStyle = color;
        ctx.font = 'bold 100px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.shadowColor = color;
        ctx.shadowBlur = 25;
        ctx.fillText(n.toString(), 100, 100);
    }

    function updateTheme() {
        isNight = document.body.classList.contains('night');
        drawNum(count);
    }

    drawNum(0);

    fetch('/api/counter')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            count = d.count || 0;
            drawNum(count);
        })
        .catch(function() {});

    canvas.addEventListener('mouseenter', function() {
        isHovering = true;
    });

    canvas.addEventListener('mouseleave', function() {
        isHovering = false;
    });

    function animate() {
        requestAnimationFrame(animate);
        
        if (isHovering) {
            rotation += 12;
        } else {
            rotation *= 0.9;
        }
        
        floatOffset += 0.05;
        var floatY = Math.sin(floatOffset) * 5;
        
        canvas.style.transform = 'translateY(' + floatY + 'px) rotateY(' + rotation + 'deg)';
        
        drawNum(count);
    }

    new MutationObserver(updateTheme).observe(document.body, { attributes: true, attributeFilter: ['class'] });

    animate();

    window.updateCrystalCount = function(n) {
        count = n;
        drawNum(count);
    };
}

window.initCrystalCounter = initCrystalCounter;
