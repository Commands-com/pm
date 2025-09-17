/**
 * ConsensusIndicator Component
 * Reusable circular progress indicator for multi-model consensus visualization
 *
 * Features:
 * - SVG-based circular progress bar
 * - Color-coded agreement levels (red/yellow/green/blue)
 * - Tooltip with model breakdown
 * - Multiple size variants
 * - Smooth animations for consensus changes
 * - Accessibility support
 */

class ConsensusIndicator {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            consensus: 0,
            size: 'medium', // small (24px), medium (48px), large (72px)
            showTooltip: true,
            modelBreakdown: null, // { total: 4, validated: 3, rejected: 1, partial: 0 }
            animationDuration: 300,
            noData: false,
            ...options
        };

        this.sizes = {
            small: { diameter: 24, strokeWidth: 3 },
            medium: { diameter: 48, strokeWidth: 4 },
            large: { diameter: 72, strokeWidth: 6 }
        };

        this.init();
    }

    init() {
        this.render();
        if (this.options.showTooltip) {
            this.setupTooltip();
        }
    }

    render() {
        const { diameter, strokeWidth } = this.sizes[this.options.size];
        const radius = (diameter - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;

        this.container.innerHTML = `
            <div class="consensus-indicator consensus-indicator--${this.options.size}"
                 role="progressbar"
                 aria-valuenow="${this.options.consensus}"
                 aria-valuemin="0"
                 aria-valuemax="100"
                 aria-label="Consensus: ${this.options.consensus}%"
                 tabindex="0">
                <svg width="${diameter}" height="${diameter}" class="consensus-svg">
                    <!-- Background circle -->
                    <circle
                        cx="${diameter / 2}"
                        cy="${diameter / 2}"
                        r="${radius}"
                        stroke="var(--consensus-bg-color)"
                        stroke-width="${strokeWidth}"
                        fill="none"
                        class="consensus-bg-circle"
                    />
                    <!-- Progress circle -->
                    <circle
                        cx="${diameter / 2}"
                        cy="${diameter / 2}"
                        r="${radius}"
                        stroke="var(--consensus-color)"
                        stroke-width="${strokeWidth}"
                        fill="none"
                        stroke-dasharray="${circumference}"
                        stroke-dashoffset="${circumference - (this.options.consensus / 100) * circumference}"
                        stroke-linecap="round"
                        class="consensus-progress-circle"
                        style="transition: stroke-dashoffset ${this.options.animationDuration}ms ease-out, stroke ${this.options.animationDuration}ms ease-out;"
                    />
                </svg>
                <div class="consensus-text">
                    <span class="consensus-percentage">${this.options.noData ? '—' : Math.round(this.options.consensus) + '%'}</span>
                </div>
                ${this.options.showTooltip ? '<div class="consensus-tooltip" style="display: none;"></div>' : ''}
            </div>
        `;

        this.updateColors();
    }

    updateColors() {
        const consensus = this.options.consensus;
        let color, bgColor;

        if (this.options.noData) {
            color = '#94a3b8'; // Slate gray for no data
        } else if (consensus < 50) {
            color = '#ef4444'; // Red
        } else if (consensus < 75) {
            color = '#f59e0b'; // Yellow/Orange
        } else if (consensus < 90) {
            color = '#10b981'; // Green
        } else {
            color = '#3b82f6'; // Blue
        }

        bgColor = '#e2e8f0'; // Light gray

        this.container.style.setProperty('--consensus-color', color);
        this.container.style.setProperty('--consensus-bg-color', bgColor);
    }

    setupTooltip() {
        const indicator = this.container.querySelector('.consensus-indicator');
        const tooltip = this.container.querySelector('.consensus-tooltip');

        if (!tooltip) return;

        indicator.addEventListener('mouseenter', () => {
            this.showTooltip();
        });

        indicator.addEventListener('mouseleave', () => {
            this.hideTooltip();
        });

        indicator.addEventListener('focus', () => {
            this.showTooltip();
        });

        indicator.addEventListener('blur', () => {
            this.hideTooltip();
        });
    }

    showTooltip() {
        const tooltip = this.container.querySelector('.consensus-tooltip');
        if (!tooltip) return;

        const breakdown = this.options.modelBreakdown;
        let content = this.options.noData ? 'No data' : `${Math.round(this.options.consensus)}% consensus`;

        if (breakdown) {
            const { total, validated, rejected, partial } = breakdown;
            content = `${validated}/${total} models agree: validated`;
            if (rejected > 0) content += `, ${rejected} rejected`;
            if (partial > 0) content += `, ${partial} partial`;
        }

        tooltip.textContent = content;
        tooltip.style.display = 'block';

        // Position tooltip
        this.positionTooltip(tooltip);
    }

    hideTooltip() {
        const tooltip = this.container.querySelector('.consensus-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    }

    positionTooltip(tooltip) {
        const indicator = this.container.querySelector('.consensus-indicator');
        const rect = indicator.getBoundingClientRect();

        tooltip.style.position = 'absolute';
        tooltip.style.top = `${rect.bottom + 8}px`;
        tooltip.style.left = `${rect.left + rect.width / 2}px`;
        tooltip.style.transform = 'translateX(-50%)';
        tooltip.style.zIndex = '1000';
    }

    /**
     * Update consensus value with animation
     */
    update(newConsensus, modelBreakdown = null) {
        this.options.consensus = Math.max(0, Math.min(100, newConsensus));
        if (modelBreakdown) {
            this.options.modelBreakdown = modelBreakdown;
        }

        const progressCircle = this.container.querySelector('.consensus-progress-circle');
        const percentageText = this.container.querySelector('.consensus-percentage');
        const indicator = this.container.querySelector('.consensus-indicator');

        if (progressCircle && percentageText && indicator) {
            const radius = parseFloat(progressCircle.getAttribute('r'));
            const circumference = 2 * Math.PI * radius;
            const offset = circumference - (this.options.consensus / 100) * circumference;

            progressCircle.style.strokeDashoffset = offset;
            percentageText.textContent = `${Math.round(this.options.consensus)}%`;
            indicator.setAttribute('aria-valuenow', this.options.consensus);
            indicator.setAttribute('aria-label', `Consensus: ${this.options.consensus}%`);

            this.updateColors();
        }
    }

    /**
     * Set size and re-render
     */
    setSize(size) {
        if (this.sizes[size]) {
            this.options.size = size;
            this.render();
            if (this.options.showTooltip) {
                this.setupTooltip();
            }
        }
    }

    /**
     * Destroy the component and clean up event listeners
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ConsensusIndicator;
}

// Global registration for direct HTML usage
if (typeof window !== 'undefined') {
    window.ConsensusIndicator = ConsensusIndicator;
}
