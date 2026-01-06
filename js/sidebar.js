export class Sidebar extends HTMLElement {
    constructor() {
        super();
        this.collapsed = false;
        this.role = localStorage.getItem('userRole') || 'doctor'; // Default to doctor for dev
    }

    connectedCallback() {
        this.render();
        this.addEventListeners();
    }

    addEventListeners() {
        // Toggle Sidebar
        const toggleBtn = this.querySelector('#toggle-sidebar');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.collapsed = !this.collapsed;
                document.body.classList.toggle('sidebar-collapsed', this.collapsed);
                this.render(); // Re-render to update text visibility
                // Re-attach event listener after re-render is tricky, so better to toggle classes
                // Actually, let's just toggle a class on the sidebar itself and CSS handle the rest
            });
        }
    }

    getNavItems() {
        const doctorItems = [
            { icon: 'home', text: 'Dashboard', link: '/doctor/dashboard.html' },
            { icon: 'users', text: 'My Patients', link: '/doctor/patients.html' },
            { icon: 'alert-triangle', text: 'Alerts', link: '/doctor/alerts.html' },
            { icon: 'shield-alert', text: 'Drug Warnings', link: '/doctor/warnings.html' },
        ];

        const pharmaItems = [
            { icon: 'activity', text: 'Overview', link: '/pharma/dashboard.html' },
            { icon: 'file-text', text: 'Reports', link: '/pharma/reports.html' },
            { icon: 'map', text: 'Demographics', link: '/pharma/demographics.html' },
        ];

        return this.role === 'pharma' ? pharmaItems : doctorItems;
    }

    render() {
        const items = this.getNavItems();

        this.innerHTML = `
            <style>
                aside {
                    width: var(--sidebar-width);
                    height: 100vh;
                    background-color: var(--white);
                    border-right: 1px solid #E2E8F0;
                    position: fixed;
                    left: 0;
                    top: 0;
                    display: flex;
                    flex-direction: column;
                    transition: width 0.3s ease;
                    z-index: 100;
                }
                
                body.sidebar-collapsed aside {
                    width: var(--sidebar-collapsed-width);
                }

                .logo-area {
                    padding: 1.5rem;
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                    border-bottom: 1px solid #F1F5F9;
                }

                .logo-icon {
                    width: 32px;
                    height: 32px;
                    background-color: var(--primary);
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                }

                .app-title {
                    font-weight: 700;
                    color: var(--primary-dark);
                    white-space: nowrap;
                    overflow: hidden;
                }
                
                body.sidebar-collapsed .app-title {
                    display: none;
                }

                nav {
                    flex: 1;
                    padding: 1rem 0;
                }

                .nav-item {
                    display: flex;
                    align-items: center;
                    padding: 0.75rem 1.5rem;
                    color: var(--text-muted);
                    text-decoration: none;
                    transition: all 0.2s;
                    gap: 1rem;
                }

                .nav-item:hover, .nav-item.active {
                    background-color: var(--secondary);
                    color: var(--primary-dark);
                    border-right: 3px solid var(--primary);
                }

                .nav-text {
                    white-space: nowrap;
                }
                
                body.sidebar-collapsed .nav-text {
                    display: none;
                }

                .user-profile {
                    padding: 1rem;
                    border-top: 1px solid #F1F5F9;
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                }

                .logout-btn {
                    margin-top: auto;
                    color: var(--risk-high);
                }
            </style>
            
            <aside>
                <div class="logo-area">
                    <div class="logo-icon">Rx</div>
                    <span class="app-title">MedSafe</span>
                </div>

                <nav>
                    ${items.map(item => `
                        <a href="${item.link}" class="nav-item ${window.location.pathname.includes(item.link) ? 'active' : ''}">
                            <i data-lucide="${item.icon}"></i>
                            <span class="nav-text">${item.text}</span>
                        </a>
                    `).join('')}
                </nav>

                <div class="user-profile">
                     <a href="/index.html" onclick="localStorage.removeItem('userRole'); localStorage.removeItem('currentUser');" class="nav-item logout-btn">
                        <i data-lucide="log-out"></i>
                        <span class="nav-text">Logout</span>
                    </a>
                </div>
            </aside>
        `;

        // Initialize Lucide icons if available globally or import them
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }
}

customElements.define('app-sidebar', Sidebar);
