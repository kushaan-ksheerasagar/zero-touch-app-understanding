/**
 * Zero-Touch App Understanding - Dashboard Logic
 * Coordinates data loading, navigation graph rendering, screenshot/overlay inspection,
 * and screen reconstruction.
 */

// Global State
let currentPack = null;
let selectedScreenId = null;
let currentViewMode = 'screenshot'; // 'screenshot' or 'reconstruct'

// Embedded sample pack for zero-dependency local file execution (fallback if fetch fails)
const FALLBACK_PACK = {
  "app_name": "ZeroShop Mobile",
  "package_name": "com.example.shop",
  "version": "1.0",
  "exploration_status": "completed",
  "design_system": {
    "theme": "dark",
    "primary_color": "#6366f1",
    "background_color": "#0b0f19",
    "surface_color": "#1e293b",
    "accent_color": "#38bdf8",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "border_radius": "12px",
    "font_family": "Inter, -apple-system, sans-serif"
  },
  "screens": {
    "screen_001": {
      "screen_id": "screen_001",
      "name": "Login",
      "purpose": "Authenticates returning users with email and password credentials.",
      "activity_name": "com.example.shop/.LoginActivity",
      "elements": [
        { "element_id": "com.example.shop:id/app_logo", "type": "android.widget.ImageView", "text": "", "content_description": "ZeroShop Logo", "bounds": [440, 160, 640, 360], "center": [540, 260], "clickable": false },
        { "element_id": "com.example.shop:id/title_login", "type": "android.widget.TextView", "text": "Sign In to ZeroShop", "bounds": [80, 390, 1000, 460], "center": [540, 425], "clickable": false },
        { "element_id": "com.example.shop:id/input_email", "type": "android.widget.EditText", "text": "", "content_description": "Email address", "bounds": [80, 500, 1000, 620], "center": [540, 560], "clickable": true, "focusable": true },
        { "element_id": "com.example.shop:id/input_password", "type": "android.widget.EditText", "text": "", "content_description": "Password", "bounds": [80, 650, 1000, 770], "center": [540, 710], "clickable": true, "focusable": true },
        { "element_id": "com.example.shop:id/btn_login", "type": "android.widget.Button", "text": "Continue", "bounds": [80, 810, 1000, 930], "center": [540, 870], "clickable": true, "purpose": "Submits credentials and transitions to Home screen" },
        { "element_id": "com.example.shop:id/link_forgot_pwd", "type": "android.widget.TextView", "text": "Forgot password?", "bounds": [360, 960, 720, 1020], "center": [540, 990], "clickable": true }
      ],
      "actions": [
        { "action_id": "act_login_continue", "action_type": "tap", "target_element_id": "com.example.shop:id/btn_login", "description": "Tap Continue button to sign in" }
      ]
    },
    "screen_002": {
      "screen_id": "screen_002",
      "name": "Home",
      "purpose": "Main marketplace discovery hub featuring featured drops and product catalog.",
      "activity_name": "com.example.shop/.MainActivity",
      "elements": [
        { "element_id": "com.example.shop:id/toolbar_title", "type": "android.widget.TextView", "text": "ZeroShop", "bounds": [48, 80, 420, 160], "center": [234, 120], "clickable": false },
        { "element_id": "com.example.shop:id/btn_search", "type": "android.widget.ImageButton", "content_description": "Search products", "bounds": [920, 80, 1032, 160], "center": [976, 120], "clickable": true, "purpose": "Opens dedicated product search view" },
        { "element_id": "com.example.shop:id/hero_banner", "type": "android.widget.ImageView", "content_description": "New Season Tech Arrivals", "bounds": [48, 190, 1032, 520], "center": [540, 355], "clickable": true },
        { "element_id": "com.example.shop:id/section_featured", "type": "android.widget.TextView", "text": "Trending Products", "bounds": [48, 550, 600, 620], "center": [324, 585], "clickable": false },
        { "element_id": "com.example.shop:id/product_card_1", "type": "androidx.cardview.widget.CardView", "content_description": "Pro Wireless Headphones", "bounds": [48, 640, 1032, 940], "center": [540, 790], "clickable": true },
        { "element_id": "com.example.shop:id/product_title_1", "type": "android.widget.TextView", "text": "Pro Wireless Headphones", "bounds": [80, 800, 750, 860], "center": [415, 830], "clickable": false },
        { "element_id": "com.example.shop:id/product_price_1", "type": "android.widget.TextView", "text": "$199.99", "bounds": [80, 870, 300, 920], "center": [190, 895], "clickable": false },
        { "element_id": "com.example.shop:id/nav_home", "type": "android.widget.TextView", "text": "Home", "bounds": [0, 1780, 360, 1920], "center": [180, 1850], "clickable": true },
        { "element_id": "com.example.shop:id/nav_search", "type": "android.widget.TextView", "text": "Search", "bounds": [360, 1780, 720, 1920], "center": [540, 1850], "clickable": true },
        { "element_id": "com.example.shop:id/nav_profile", "type": "android.widget.TextView", "text": "Profile", "bounds": [720, 1780, 1080, 1920], "center": [900, 1850], "clickable": true }
      ],
      "actions": [
        { "action_id": "act_home_tap_search", "action_type": "tap", "target_element_id": "com.example.shop:id/btn_search", "description": "Tap search button in toolbar" },
        { "action_id": "act_home_tap_profile", "action_type": "tap", "target_element_id": "com.example.shop:id/nav_profile", "description": "Tap Profile tab in bottom navigation" }
      ]
    },
    "screen_003": {
      "screen_id": "screen_003",
      "name": "Search",
      "purpose": "Real-time search interface with query bar, category filters, and product results.",
      "activity_name": "com.example.shop/.SearchActivity",
      "elements": [
        { "element_id": "com.example.shop:id/btn_back_search", "type": "android.widget.ImageButton", "content_description": "Navigate back", "bounds": [32, 70, 120, 160], "center": [76, 115], "clickable": true },
        { "element_id": "com.example.shop:id/input_search_query", "type": "android.widget.EditText", "text": "Headphones", "content_description": "Search products", "bounds": [140, 70, 1032, 160], "center": [586, 115], "clickable": true, "focusable": true },
        { "element_id": "com.example.shop:id/chip_audio", "type": "android.widget.Button", "text": "Audio", "bounds": [48, 180, 240, 250], "center": [144, 215], "clickable": true },
        { "element_id": "com.example.shop:id/search_result_1", "type": "android.view.ViewGroup", "content_description": "Noise-Canceling Pro Headset", "bounds": [48, 280, 1032, 540], "center": [540, 410], "clickable": true },
        { "element_id": "com.example.shop:id/result_title_1", "type": "android.widget.TextView", "text": "Noise-Canceling Pro Headset", "bounds": [280, 310, 980, 380], "center": [630, 345], "clickable": false },
        { "element_id": "com.example.shop:id/result_price_1", "type": "android.widget.TextView", "text": "$149.00", "bounds": [280, 400, 500, 460], "center": [390, 430], "clickable": false }
      ],
      "actions": [
        { "action_id": "act_search_pick_product", "action_type": "tap", "target_element_id": "com.example.shop:id/search_result_1", "description": "Tap product result to view details" },
        { "action_id": "act_search_back", "action_type": "back", "description": "Press back to return to Home" }
      ]
    },
    "screen_004": {
      "screen_id": "screen_004",
      "name": "Product Details",
      "purpose": "Detailed product presentation with high-res imagery, specifications, and purchase CTA.",
      "activity_name": "com.example.shop/.ProductDetailActivity",
      "elements": [
        { "element_id": "com.example.shop:id/btn_back_detail", "type": "android.widget.ImageButton", "content_description": "Back", "bounds": [32, 70, 120, 160], "center": [76, 115], "clickable": true },
        { "element_id": "com.example.shop:id/product_hero_img", "type": "android.widget.ImageView", "content_description": "Photo of Noise-Canceling Pro Headset", "bounds": [48, 180, 1032, 780], "center": [540, 480], "clickable": false },
        { "element_id": "com.example.shop:id/detail_title", "type": "android.widget.TextView", "text": "Noise-Canceling Pro Headset", "bounds": [48, 810, 1000, 880], "center": [524, 845], "clickable": false },
        { "element_id": "com.example.shop:id/detail_rating", "type": "android.widget.TextView", "text": "4.9 (2,410 customer reviews)", "bounds": [48, 890, 560, 940], "center": [304, 915], "clickable": false },
        { "element_id": "com.example.shop:id/detail_price", "type": "android.widget.TextView", "text": "$149.00", "bounds": [48, 960, 320, 1030], "center": [184, 995], "clickable": false },
        { "element_id": "com.example.shop:id/detail_desc", "type": "android.widget.TextView", "text": "Engineered for immersive studio-grade sound with adaptive hybrid ANC and 45h runtime.", "bounds": [48, 1050, 1032, 1200], "center": [540, 1125], "clickable": false },
        { "element_id": "com.example.shop:id/btn_add_cart", "type": "android.widget.Button", "text": "Add to Cart - $149.00", "bounds": [48, 1740, 1032, 1870], "center": [540, 1805], "clickable": true }
      ],
      "actions": [
        { "action_id": "act_product_back_action", "action_type": "back", "description": "Press Back to return to Search" }
      ]
    },
    "screen_005": {
      "screen_id": "screen_005",
      "name": "Profile",
      "purpose": "User management screen displaying account info, past orders, and application settings.",
      "activity_name": "com.example.shop/.ProfileActivity",
      "elements": [
        { "element_id": "com.example.shop:id/profile_avatar", "type": "android.widget.ImageView", "content_description": "User avatar photo", "bounds": [440, 140, 640, 340], "center": [540, 240], "clickable": false },
        { "element_id": "com.example.shop:id/user_name", "type": "android.widget.TextView", "text": "Alex Mercer", "bounds": [80, 370, 1000, 440], "center": [540, 405], "clickable": false },
        { "element_id": "com.example.shop:id/user_email", "type": "android.widget.TextView", "text": "alex.mercer@example.com", "bounds": [80, 450, 1000, 510], "center": [540, 480], "clickable": false },
        { "element_id": "com.example.shop:id/menu_orders", "type": "android.widget.TextView", "text": "Order History", "bounds": [60, 560, 1020, 660], "center": [540, 610], "clickable": true },
        { "element_id": "com.example.shop:id/menu_settings", "type": "android.widget.TextView", "text": "Preferences & Security", "bounds": [60, 680, 1020, 780], "center": [540, 730], "clickable": true },
        { "element_id": "com.example.shop:id/btn_logout", "type": "android.widget.Button", "text": "Sign Out", "bounds": [60, 840, 1020, 950], "center": [540, 895], "clickable": true },
        { "element_id": "com.example.shop:id/nav_home_from_profile", "type": "android.widget.TextView", "text": "Home", "bounds": [0, 1780, 360, 1920], "center": [180, 1850], "clickable": true }
      ],
      "actions": [
        { "action_id": "act_profile_tap_home", "action_type": "tap", "target_element_id": "com.example.shop:id/nav_home_from_profile", "description": "Tap Home tab in bottom navigation" }
      ]
    }
  },
  "transitions": [
    { "transition_id": "trans_001", "source_screen_id": "screen_001", "destination_screen_id": "screen_002", "action": { "action_id": "act_login_continue", "action_type": "tap", "target_element_id": "com.example.shop:id/btn_login", "description": "Tap Continue button to sign in" } },
    { "transition_id": "trans_002", "source_screen_id": "screen_002", "destination_screen_id": "screen_003", "action": { "action_id": "act_home_tap_search", "action_type": "tap", "target_element_id": "com.example.shop:id/btn_search", "description": "Tap search button in toolbar" } },
    { "transition_id": "trans_003", "source_screen_id": "screen_003", "destination_screen_id": "screen_004", "action": { "action_id": "act_search_pick_product", "action_type": "tap", "target_element_id": "com.example.shop:id/search_result_1", "description": "Tap product result to view details" } },
    { "transition_id": "trans_004", "source_screen_id": "screen_004", "destination_screen_id": "screen_003", "action": { "action_id": "act_product_back_action", "action_type": "back", "description": "Press Back to return to Search" } },
    { "transition_id": "trans_005", "source_screen_id": "screen_002", "destination_screen_id": "screen_005", "action": { "action_id": "act_home_tap_profile", "action_type": "tap", "target_element_id": "com.example.shop:id/nav_profile", "description": "Tap Profile tab in bottom navigation" } },
    { "transition_id": "trans_006", "source_screen_id": "screen_005", "destination_screen_id": "screen_002", "action": { "action_id": "act_profile_tap_home", "action_type": "tap", "target_element_id": "com.example.shop:id/nav_home_from_profile", "description": "Tap Home tab in bottom navigation" } }
  ],
  "navigation_graph": {
    "nodes": [
      { "id": "screen_001", "label": "Login", "activity": "com.example.shop/.LoginActivity", "element_count": 6, "is_root": true },
      { "id": "screen_002", "label": "Home", "activity": "com.example.shop/.MainActivity", "element_count": 10, "is_root": false },
      { "id": "screen_003", "label": "Search", "activity": "com.example.shop/.SearchActivity", "element_count": 6, "is_root": false },
      { "id": "screen_004", "label": "Product Details", "activity": "com.example.shop/.ProductDetailActivity", "element_count": 7, "is_root": false },
      { "id": "screen_005", "label": "Profile", "activity": "com.example.shop/.ProfileActivity", "element_count": 7, "is_root": false }
    ],
    "edges": [
      { "id": "trans_001", "source": "screen_001", "target": "screen_002", "label": "tap: Continue", "action_type": "tap" },
      { "id": "trans_002", "source": "screen_002", "target": "screen_003", "label": "tap: Search", "action_type": "tap" },
      { "id": "trans_003", "source": "screen_003", "target": "screen_004", "label": "tap: Product Card", "action_type": "tap" },
      { "id": "trans_004", "source": "screen_004", "target": "screen_003", "label": "back", "action_type": "back" },
      { "id": "trans_005", "source": "screen_002", "target": "screen_005", "label": "tap: Profile", "action_type": "tap" },
      { "id": "trans_006", "source": "screen_005", "target": "screen_002", "label": "tap: Home", "action_type": "tap" }
    ]
  }
};

// Application Bootstrap
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadKnowledgePack();
});

function initEventListeners() {
  // Tab Switching (Screenshot View vs Reconstructed View)
  document.querySelectorAll('.view-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
      e.target.classList.add('active');
      currentViewMode = e.target.dataset.mode;
      renderCurrentScreenView();
    });
  });

  // Custom JSON Upload
  const fileInput = document.getElementById('json-file-input');
  if (fileInput) {
    fileInput.addEventListener('change', handleFileUpload);
  }
}

async function loadKnowledgePack() {
  try {
    const response = await fetch('../knowledge/sample_knowledge_pack.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    currentPack = await response.json();
  } catch (err) {
    console.warn('Could not fetch sample_knowledge_pack.json via network (likely local file:// origin). Using embedded sample pack.', err);
    currentPack = FALLBACK_PACK;
  }
  renderDashboard();
}

function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      currentPack = JSON.parse(e.target.result);
      renderDashboard();
    } catch (err) {
      alert('Failed to parse JSON file: ' + err.message);
    }
  };
  reader.readAsText(file);
}

function renderDashboard() {
  if (!currentPack) return;

  // 1. Header Information & KPIs
  document.getElementById('app-name').textContent = currentPack.app_name || 'Android App';
  document.getElementById('package-name').textContent = currentPack.package_name || 'unknown.pkg';
  document.getElementById('status-text').textContent = (currentPack.exploration_status || 'Completed').toUpperCase();

  const screens = Object.values(currentPack.screens || {});
  let totalElements = 0;
  screens.forEach(s => {
    totalElements += (s.elements || []).length;
  });

  document.getElementById('kpi-screens').textContent = screens.length;
  document.getElementById('kpi-elements').textContent = totalElements;
  document.getElementById('kpi-transitions').textContent = (currentPack.transitions || []).length;

  // 2. Select initial screen
  if (!selectedScreenId || !currentPack.screens[selectedScreenId]) {
    selectedScreenId = screens[0]?.screen_id || null;
  }

  // 3. Render Screen List
  renderScreenList();

  // 4. Render Navigation Graph
  renderNavigationGraph();

  // 5. Render Center & Right Panels
  renderCurrentScreenView();
  renderScreenInspector();
}

function renderScreenList() {
  const container = document.getElementById('screen-list');
  if (!container) return;
  container.innerHTML = '';

  const screens = Object.values(currentPack.screens || {});
  screens.forEach(screen => {
    const item = document.createElement('div');
    item.className = `screen-list-item ${screen.screen_id === selectedScreenId ? 'active' : ''}`;
    item.onclick = () => selectScreen(screen.screen_id);

    item.innerHTML = `
      <div class="screen-item-info">
        <span class="screen-item-name">${escapeHtml(screen.name)}</span>
        <span class="screen-item-id">${screen.screen_id}</span>
      </div>
      <span class="screen-item-badge">${(screen.elements || []).length} elems</span>
    `;
    container.appendChild(item);
  });
}

function renderNavigationGraph() {
  const container = document.getElementById('nav-graph-svg');
  if (!container) return;

  const graph = currentPack.navigation_graph || { nodes: [], edges: [] };
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];

  // Layout calculations for directed tree/flow graph
  const width = 290;
  const height = 320;
  
  // Deterministic positions for nodes in a clean vertical/horizontal flowchart
  const nodePositions = {
    'screen_001': { x: 145, y: 35 },
    'screen_002': { x: 145, y: 110 },
    'screen_003': { x: 75,  y: 195 },
    'screen_004': { x: 75,  y: 275 },
    'screen_005': { x: 215, y: 195 },
  };

  let svgHtml = `
    <defs>
      <marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748b" />
      </marker>
      <marker id="arrow-active" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#38bdf8" />
      </marker>
    </defs>
  `;

  // Draw Edges
  edges.forEach((edge, idx) => {
    const sPos = nodePositions[edge.source];
    const tPos = nodePositions[edge.target];
    if (!sPos || !tPos) return;

    const isActive = (edge.source === selectedScreenId || edge.target === selectedScreenId);
    const marker = isActive ? 'url(#arrow-active)' : 'url(#arrow)';

    // Simple curved line
    const dx = tPos.x - sPos.x;
    const dy = tPos.y - sPos.y;
    const cx = sPos.x + dx * 0.5 + (idx % 2 === 0 ? 10 : -10);
    const cy = sPos.y + dy * 0.5;

    svgHtml += `
      <g class="graph-edge ${isActive ? 'active' : ''}">
        <path d="M ${sPos.x} ${sPos.y} Q ${cx} ${cy} ${tPos.x} ${tPos.y}" marker-end="${marker}" />
      </g>
    `;
  });

  // Draw Nodes
  nodes.forEach(node => {
    const pos = nodePositions[node.id] || { x: 145, y: 160 };
    const isActive = (node.id === selectedScreenId);
    const boxW = 86;
    const boxH = 34;

    svgHtml += `
      <g class="graph-node ${isActive ? 'active' : ''}" onclick="selectScreen('${node.id}')">
        <rect x="${pos.x - boxW / 2}" y="${pos.y - boxH / 2}" width="${boxW}" height="${boxH}" />
        <text x="${pos.x}" y="${pos.y + 4}">${escapeHtml(node.label)}</text>
      </g>
    `;
  });

  container.innerHTML = svgHtml;
}

function selectScreen(screenId) {
  selectedScreenId = screenId;
  renderScreenList();
  renderNavigationGraph();
  renderCurrentScreenView();
  renderScreenInspector();
}

function renderCurrentScreenView() {
  const screenshotContainer = document.getElementById('screenshot-view');
  const reconContainer = document.getElementById('reconstruct-view');
  const screen = currentPack.screens[selectedScreenId];

  if (!screen) return;

  if (currentViewMode === 'screenshot') {
    screenshotContainer.style.display = 'block';
    reconContainer.style.display = 'none';
    renderMockScreenshot(screen);
  } else {
    screenshotContainer.style.display = 'none';
    reconContainer.style.display = 'block';
    reconContainer.innerHTML = ScreenReconstructor.render(screen, currentPack.design_system);
  }
}

function renderMockScreenshot(screen) {
  const container = document.getElementById('screenshot-view');
  const elements = screen.elements || [];

  // 1080x1920 coordinate space
  let svgContent = `
    <svg class="mock-screenshot-svg" viewBox="0 0 1080 1920" preserveAspectRatio="xMidYMid meet">
      <!-- Phone Canvas Background -->
      <rect width="1080" height="1920" fill="#0b0f19" />
  `;

  // Draw decorative representations of elements for mock screenshot
  elements.forEach(elem => {
    const b = elem.bounds || [0, 0, 0, 0];
    const w = b[2] - b[0];
    const h = b[3] - b[1];
    const type = elem.type.toLowerCase();

    if (type.includes('button') && !type.includes('image')) {
      svgContent += `
        <rect x="${b[0]}" y="${b[1]}" width="${w}" height="${h}" rx="16" fill="#4f46e5" />
        <text x="${b[0] + w / 2}" y="${b[1] + h / 2 + 12}" fill="#ffffff" font-size="34" font-weight="bold" text-anchor="middle">${escapeHtml(elem.text)}</text>
      `;
    } else if (type.includes('edittext')) {
      svgContent += `
        <rect x="${b[0]}" y="${b[1]}" width="${w}" height="${h}" rx="16" fill="#1e293b" stroke="#334155" stroke-width="3" />
        <text x="${b[0] + 30}" y="${b[1] + h / 2 + 10}" fill="#64748b" font-size="30">${escapeHtml(elem.content_description || elem.text || 'Enter text...')}</text>
      `;
    } else if (type.includes('image')) {
      svgContent += `
        <rect x="${b[0]}" y="${b[1]}" width="${w}" height="${h}" rx="16" fill="#162032" stroke="#334155" stroke-width="2" />
        <text x="${b[0] + w / 2}" y="${b[1] + h / 2 + 10}" fill="#64748b" font-size="28" text-anchor="middle">${escapeHtml(elem.content_description || 'Image')}</text>
      `;
    } else if (elem.text) {
      const fontSize = elem.element_id.includes('title') ? 48 : (elem.element_id.includes('price') ? 38 : 28);
      const fontWeight = elem.element_id.includes('title') || elem.element_id.includes('price') ? 'bold' : 'normal';
      const fill = elem.element_id.includes('price') ? '#38bdf8' : '#f8fafc';
      svgContent += `
        <text x="${b[0] + 10}" y="${b[1] + h * 0.7}" fill="${fill}" font-size="${fontSize}" font-weight="${fontWeight}">${escapeHtml(elem.text)}</text>
      `;
    } else {
      svgContent += `
        <rect x="${b[0]}" y="${b[1]}" width="${w}" height="${h}" rx="8" fill="#1e293b" opacity="0.3" />
      `;
    }
  });

  svgContent += `</svg>`;

  // Create interactive bounding box overlays
  let bboxHtml = `<div class="bounding-box-overlay">`;
  elements.forEach(elem => {
    const b = elem.bounds || [0, 0, 0, 0];
    const leftPct = (b[0] / 1080) * 100;
    const topPct = (b[1] / 1920) * 100;
    const widthPct = ((b[2] - b[0]) / 1080) * 100;
    const heightPct = ((b[3] - b[1]) / 1920) * 100;

    bboxHtml += `
      <div 
        class="bbox" 
        id="bbox-${sanitizeId(elem.element_id)}"
        style="left: ${leftPct}%; top: ${topPct}%; width: ${widthPct}%; height: ${heightPct}%;"
        title="${escapeHtml(elem.element_id)}"
        onmouseenter="highlightElement('${sanitizeId(elem.element_id)}')"
        onmouseleave="clearHighlight('${sanitizeId(elem.element_id)}')"
      ></div>
    `;
  });
  bboxHtml += `</div>`;

  container.innerHTML = svgContent + bboxHtml;
}

function renderScreenInspector() {
  const screen = currentPack.screens[selectedScreenId];
  if (!screen) return;

  // Metadata
  document.getElementById('insp-screen-name').textContent = screen.name;
  document.getElementById('insp-screen-id').textContent = screen.screen_id;
  document.getElementById('insp-purpose').textContent = screen.purpose || 'No description provided.';
  document.getElementById('insp-activity').textContent = screen.activity_name || 'N/A';

  // Available Actions
  const actionsContainer = document.getElementById('insp-actions-list');
  actionsContainer.innerHTML = '';
  const actions = screen.actions || [];
  if (actions.length === 0) {
    actionsContainer.innerHTML = '<span style="color: var(--text-muted); font-size: 0.8rem;">No explicit actions mapped.</span>';
  } else {
    actions.forEach(act => {
      const card = document.createElement('div');
      card.className = 'action-card';
      card.innerHTML = `
        <span>${escapeHtml(act.description || act.action_id)}</span>
        <span class="action-type-pill">${act.action_type}</span>
      `;
      actionsContainer.appendChild(card);
    });
  }

  // UI Elements Table
  const tbody = document.getElementById('elements-table-body');
  tbody.innerHTML = '';
  const elements = screen.elements || [];

  elements.forEach(elem => {
    const tr = document.createElement('tr');
    tr.id = `row-${sanitizeId(elem.element_id)}`;
    tr.onmouseenter = () => highlightElement(sanitizeId(elem.element_id));
    tr.onmouseleave = () => clearHighlight(sanitizeId(elem.element_id));

    const simpleType = (elem.type || '').split('.').pop();
    const isClickable = elem.clickable ? '<span class="elem-badge-clickable">TAP</span>' : '';

    tr.innerHTML = `
      <td style="font-family: monospace; font-size: 0.72rem;">${escapeHtml(elem.element_id.split(':id/').pop())}</td>
      <td>${escapeHtml(simpleType)} ${isClickable}</td>
      <td>${escapeHtml(elem.text || elem.content_description || '-')}</td>
      <td style="font-family: monospace;">[${elem.center ? elem.center.join(',') : ''}]</td>
    `;
    tbody.appendChild(tr);
  });
}

function highlightElement(safeId) {
  const bbox = document.getElementById(`bbox-${safeId}`);
  if (bbox) bbox.classList.add('highlighted');

  const row = document.getElementById(`row-${safeId}`);
  if (row) {
    row.classList.add('highlighted');
    row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function clearHighlight(safeId) {
  const bbox = document.getElementById(`bbox-${safeId}`);
  if (bbox) bbox.classList.remove('highlighted');

  const row = document.getElementById(`row-${safeId}`);
  if (row) row.classList.remove('highlighted');
}

function sanitizeId(id) {
  return String(id).replace(/[^a-zA-Z0-9_-]/g, '_');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
