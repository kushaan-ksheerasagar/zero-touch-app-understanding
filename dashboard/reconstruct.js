/**
 * Screen Reconstruction Engine.
 * 
 * Reconstructs a visual HTML/CSS screen directly from Knowledge Pack ScreenData,
 * demonstrating autonomous UI recreation without relying on the original Android application.
 */

class ScreenReconstructor {
  /**
   * Reconstruct a screen into an HTML string and DOM tree.
   * @param {Object} screen - ScreenData object from Knowledge Pack.
   * @param {Object} designSystem - App-wide design system tokens.
   * @returns {string} HTML representation.
   */
  static render(screen, designSystem = {}) {
    if (!screen || !screen.elements) {
      return '<div class="recon-empty">No screen data available for reconstruction.</div>';
    }

    const design = {
      primary: screen.design?.primary_color || designSystem.primary_color || '#6366f1',
      bg: screen.design?.background_color || designSystem.background_color || '#0b0f19',
      surface: screen.design?.surface_color || designSystem.surface_color || '#1e293b',
      textPrimary: designSystem.text_primary || '#f8fafc',
      textSecondary: designSystem.text_secondary || '#94a3b8',
      radius: designSystem.border_radius || '12px',
      font: designSystem.font_family || 'Inter, sans-serif'
    };

    const elements = screen.elements || [];

    // Separate elements into structural roles
    const topBarElements = [];
    const bottomNavElements = [];
    const bodyElements = [];

    elements.forEach(elem => {
      const type = (elem.type || '').toLowerCase();
      const id = (elem.element_id || '').toLowerCase();
      const bounds = elem.bounds || [0, 0, 1080, 1920];
      const y = bounds[1];

      if (id.includes('nav_') && y > 1600) {
        bottomNavElements.push(elem);
      } else if (y < 220 && (type.includes('toolbar') || id.includes('toolbar') || id.includes('title_login') || id.includes('app_logo'))) {
        topBarElements.push(elem);
      } else {
        bodyElements.push(elem);
      }
    });

    let html = `
      <div class="recon-phone" style="--recon-primary: ${design.primary}; --recon-bg: ${design.bg}; --recon-surface: ${design.surface}; --recon-text: ${design.textPrimary}; --recon-subtext: ${design.textSecondary}; --recon-radius: ${design.radius}; font-family: ${design.font};">
        
        <!-- Status Bar -->
        <div class="recon-status-bar">
          <span class="recon-time">9:41</span>
          <div class="recon-status-icons">
            <span class="recon-icon">5G</span>
            <span class="recon-icon">100%</span>
          </div>
        </div>

        <!-- Screen Content Container -->
        <div class="recon-viewport">
    `;

    // Render Top Bar / Header
    if (topBarElements.length > 0) {
      html += `<div class="recon-header">`;
      topBarElements.forEach(elem => {
        html += ScreenReconstructor._renderElement(elem, design);
      });
      html += `</div>`;
    }

    // Render Body Elements
    html += `<div class="recon-body">`;
    bodyElements.forEach(elem => {
      html += ScreenReconstructor._renderElement(elem, design);
    });
    html += `</div>`;

    // Render Bottom Navigation Bar
    if (bottomNavElements.length > 0) {
      html += `<div class="recon-bottom-nav">`;
      bottomNavElements.forEach(elem => {
        const text = elem.text || elem.content_description || 'Tab';
        const isActive = elem.element_id.includes('home') || elem.element_id.includes('search');
        html += `
          <div class="recon-nav-item ${isActive ? 'active' : ''}">
            <div class="recon-nav-icon"></div>
            <span class="recon-nav-label">${ScreenReconstructor._escapeHtml(text)}</span>
          </div>
        `;
      });
      html += `</div>`;
    }

    html += `
        </div>
      </div>
    `;

    return html;
  }

  /**
   * Render individual element mapping Android widgets to clean web components.
   */
  static _renderElement(elem, design) {
    const type = (elem.type || '').toLowerCase();
    const id = elem.element_id || '';
    const text = ScreenReconstructor._escapeHtml(elem.text || '');
    const desc = ScreenReconstructor._escapeHtml(elem.content_description || '');
    const isClickable = Boolean(elem.clickable);

    // 1. Button / CTA
    if (type.includes('button') && !type.includes('imagebutton')) {
      const label = text || desc || 'Action Button';
      return `
        <button class="recon-btn" data-element-id="${id}" title="${id}">
          ${label}
        </button>
      `;
    }

    // 2. ImageButton / Icon Button
    if (type.includes('imagebutton')) {
      const label = desc || text || 'Icon';
      return `
        <button class="recon-icon-btn" data-element-id="${id}" title="${id} (${label})">
          <span class="recon-icon-glyph">🔍</span>
        </button>
      `;
    }

    // 3. EditText / Input Field
    if (type.includes('edittext')) {
      const placeholder = desc || text || 'Enter text...';
      const isPassword = id.toLowerCase().includes('password');
      return `
        <div class="recon-input-group" data-element-id="${id}">
          ${desc ? `<label class="recon-label">${desc}</label>` : ''}
          <input 
            type="${isPassword ? 'password' : 'text'}" 
            class="recon-input" 
            placeholder="${placeholder}" 
            value="${text}" 
            readonly 
          />
        </div>
      `;
    }

    // 4. ImageView / Images / Logos
    if (type.includes('imageview') || type.includes('image')) {
      return `
        <div class="recon-image-box" data-element-id="${id}">
          <div class="recon-image-placeholder">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
            <span class="recon-image-caption">${desc || 'Image Asset'}</span>
          </div>
        </div>
      `;
    }

    // 5. CardView / Container cards
    if (type.includes('cardview')) {
      return `
        <div class="recon-card" data-element-id="${id}">
          <div class="recon-card-badge">Card Item</div>
        </div>
      `;
    }

    // 6. TextView / Labels / Headings / Subtitles
    if (type.includes('textview') || text) {
      if (id.includes('title') || id.includes('heading')) {
        return `<h2 class="recon-heading" data-element-id="${id}">${text}</h2>`;
      }
      if (id.includes('price') || text.startsWith('$')) {
        return `<div class="recon-price-tag" data-element-id="${id}">${text}</div>`;
      }
      if (id.includes('rating') || text.includes('★')) {
        return `<div class="recon-rating-badge" data-element-id="${id}">${text}</div>`;
      }
      if (isClickable || id.includes('link')) {
        return `<a class="recon-link" href="#" data-element-id="${id}">${text}</a>`;
      }
      return `<p class="recon-paragraph" data-element-id="${id}">${text}</p>`;
    }

    // Fallback Container
    if (desc) {
      return `<div class="recon-generic-box" data-element-id="${id}"><span>${desc}</span></div>`;
    }

    return '';
  }

  static _escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

// Export for browser window or Node/module environment
if (typeof window !== 'undefined') {
  window.ScreenReconstructor = ScreenReconstructor;
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ScreenReconstructor;
}
