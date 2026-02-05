
// 简约白色主题 - Three.js 动态粒子波浪背景

document.addEventListener('DOMContentLoaded', () => {
    // 创建容器
    const container = document.createElement('div');
    container.id = 'canvas-container';
    document.body.prepend(container);

    // 场景设置
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc); // 与CSS背景色一致

    // 相机
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 1, 10000);
    camera.position.z = 1000;
    camera.position.y = 300; // 稍微俯视

    // 渲染器
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    // 粒子波浪参数
    const SEPARATION = 100, AMOUNTX = 50, AMOUNTY = 50;
    let particles, count = 0;

    // 创建粒子
    const numParticles = AMOUNTX * AMOUNTY;
    const positions = new Float32Array(numParticles * 3);
    const scales = new Float32Array(numParticles);

    let i = 0, j = 0;
    for (let ix = 0; ix < AMOUNTX; ix++) {
        for (let iy = 0; iy < AMOUNTY; iy++) {
            positions[i] = ix * SEPARATION - ((AMOUNTX * SEPARATION) / 2); // x
            positions[i + 1] = 0; // y
            positions[i + 2] = iy * SEPARATION - ((AMOUNTY * SEPARATION) / 2); // z
            scales[j] = 1;
            i += 3;
            j++;
        }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('scale', new THREE.BufferAttribute(scales, 1));

    // 材质 - 使用简约的淡蓝色点
    const material = new THREE.ShaderMaterial({
        uniforms: {
            color: { value: new THREE.Color(0x6366f1) }, // 品牌紫
        },
        vertexShader: `
            attribute float scale;
            void main() {
                vec4 mvPosition = modelViewMatrix * vec4( position, 1.0 );
                gl_PointSize = scale * ( 300.0 / - mvPosition.z );
                gl_Position = projectionMatrix * mvPosition;
            }
        `,
        fragmentShader: `
            uniform vec3 color;
            void main() {
                if ( length( gl_PointCoord - vec2( 0.5, 0.5 ) ) > 0.475 ) discard;
                gl_FragColor = vec4( color, 0.3 ); // 0.3 透明度
            }
        `
    });

    particles = new THREE.Points(geometry, material);
    scene.add(particles);

    // 动画循环
    function animate() {
        requestAnimationFrame(animate);
        render();
    }

    function render() {
        const positions = particles.geometry.attributes.position.array;
        const scales = particles.geometry.attributes.scale.array;

        let i = 0, j = 0;
        for (let ix = 0; ix < AMOUNTX; ix++) {
            for (let iy = 0; iy < AMOUNTY; iy++) {
                // 正弦波浪运动
                positions[i + 1] = (Math.sin((ix + count) * 0.3) * 50) +
                    (Math.sin((iy + count) * 0.5) * 50);

                // 大小变化
                scales[j] = (Math.sin((ix + count) * 0.3) + 1) * 8 +
                    (Math.sin((iy + count) * 0.5) + 1) * 8;

                i += 3;
                j++;
            }
        }

        particles.geometry.attributes.position.needsUpdate = true;
        particles.geometry.attributes.scale.needsUpdate = true;

        count += 0.1;

        // 缓慢旋转视角
        camera.position.x += (mouseX - camera.position.x) * 0.05;
        camera.position.y += (-mouseY + 200 - camera.position.y) * 0.05;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
    }

    // 交互
    let mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', (event) => {
        mouseX = (event.clientX - window.innerWidth / 2) * 1; // 灵敏度
        mouseY = (event.clientY - window.innerHeight / 2) * 1;
    });

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    animate();
});
