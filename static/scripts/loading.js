// Bouncing-logo loading screen (DVD screensaver style).
// Usage: startLoadingScreen(canvasElement, logoUrl)
let speed = 20;
let scale = 0.17; // Image scale (I work on 1080p monitor)

function startLoadingScreen(canvas, logoSrc) {
    const ctx = canvas.getContext("2d");
    let logoColor = pickColor();
    const dvd = {
        x: 200,
        y: 200,
        xspeed: 10,
        yspeed: 10,
        img: new Image()
    };
    dvd.img.src = logoSrc;
    dvd.img.width = 800;
    dvd.img.height = 800;

    function resize() {
        //Draw the "tv screen"
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    function update() {
        //Draw the canvas background
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.font = "48px comic sans ms";
        ctx.fillStyle = '#FFFFFF';
        ctx.fillText("Loading....", canvas.width/2 - 100, canvas.height/2);
        //Draw DVD Logo and his background
        ctx.fillStyle = logoColor;
        ctx.fillRect(dvd.x, dvd.y, dvd.img.width*scale, dvd.img.height*scale);
        ctx.drawImage(dvd.img, dvd.x, dvd.y, dvd.img.width*scale, dvd.img.height*scale);
        //Move the logo
        dvd.x+=dvd.xspeed;
        dvd.y+=dvd.yspeed;
        //Check for collision
        checkHitBox();
        setTimeout(update, speed);
    }

    //Check for border collision
    function checkHitBox() {
        if (dvd.x+dvd.img.width*scale >= canvas.width || dvd.x <= 0) {
            dvd.xspeed *= -1;
            logoColor = pickColor();
        }

        if (dvd.y+dvd.img.height*scale >= canvas.height || dvd.y <= 0) {
            dvd.yspeed *= -1;
            logoColor = pickColor();
        }
    }

    resize();
    window.addEventListener("resize", resize);
    update();
}

//Pick a random color in RGB format
function pickColor() {
    const r = Math.random() * 254;
    const g = Math.random() * 254;
    const b = Math.random() * 254;
    return 'rgb('+r+','+g+', '+b+')';
}
