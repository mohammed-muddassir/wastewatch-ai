/**
 * WasteWatch AI - Frontend JavaScript
 * Handles all interactive functionality for the dashboard.
 */

// ===== Toast Notifications =====

function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️',
        warning: '⚠️'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || icons.info}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.classList.add('toast-out'); setTimeout(() => this.parentElement.remove(), 300)">×</button>
    `;

    container.appendChild(toast);

    // Auto-remove after duration
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('toast-out');
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}


// ===== API Helpers =====

async function apiCall(url, method = 'POST', data = null) {
    try {
        const options = {
            method: method,
            headers: { 'Content-Type': 'application/json' },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || `HTTP ${response.status}`);
        }

        return result;
    } catch (error) {
        console.error(`API Error [${url}]:`, error);
        throw error;
    }
}


// ===== Button Loading State =====

function setButtonLoading(btnId, loading = true) {
    const btn = document.getElementById(btnId);
    if (!btn) return;

    if (loading) {
        btn.classList.add('btn-loading');
        btn.disabled = true;
        btn._originalText = btn.innerHTML;
        const icon = btn.querySelector('svg');
        const iconHtml = icon ? icon.outerHTML : '';
        const text = btn.querySelector('span');
        if (text) {
            text.textContent = 'Processing...';
        }
    } else {
        btn.classList.remove('btn-loading');
        btn.disabled = false;
        if (btn._originalText) {
            btn.innerHTML = btn._originalText;
            lucide.createIcons();
        }
    }
}


// ===== Pipeline Actions =====

async function scrapeNow() {
    setButtonLoading('btn-scrape', true);
    setButtonLoading('scrape-now-btn', true);
    setButtonLoading('btn-scrape-articles', true);

    showToast('🔍 Starting news scrape...', 'info');

    try {
        const result = await apiCall('/api/scrape');

        if (result.success) {
            showToast(
                `Found ${result.data.found} articles, ${result.data.new} new!`,
                result.data.new > 0 ? 'success' : 'info'
            );

            if (result.data.new > 0) {
                setTimeout(() => location.reload(), 1500);
            }
        }
    } catch (error) {
        showToast(`Scrape failed: ${error.message}`, 'error');
    } finally {
        setButtonLoading('btn-scrape', false);
        setButtonLoading('scrape-now-btn', false);
        setButtonLoading('btn-scrape-articles', false);
    }
}


function getCustomPrompt() {
    const el = document.getElementById('dashboard-custom-prompt');
    return el ? el.value.trim() : '';
}

function togglePromptSection() {
    const toggle = document.getElementById('prompt-toggle');
    const body = document.getElementById('prompt-body');
    if (toggle && body) {
        toggle.classList.toggle('expanded');
        body.classList.toggle('visible');
    }
}


async function generateBlogs() {
    setButtonLoading('btn-generate', true);
    setButtonLoading('btn-generate-all-articles', true);
    setButtonLoading('btn-generate-blogs', true);

    showToast('✨ Generating blog posts with AI...', 'info');

    try {
        const payload = { limit: 5 };
        const prompt = getCustomPrompt();
        if (prompt) payload.prompt = prompt;

        const result = await apiCall('/api/generate', 'POST', payload);

        if (result.success) {
            showToast(`Generated ${result.generated} blog posts!`, 'success');

            if (result.generated > 0) {
                setTimeout(() => location.reload(), 1500);
            }
        }
    } catch (error) {
        showToast(`Generation failed: ${error.message}`, 'error');
    } finally {
        setButtonLoading('btn-generate', false);
        setButtonLoading('btn-generate-all-articles', false);
        setButtonLoading('btn-generate-blogs', false);
    }
}


async function generateSingle(articleId) {
    showToast('✨ Generating blog post...', 'info');

    try {
        const payload = {};
        const prompt = getCustomPrompt();
        if (prompt) payload.prompt = prompt;

        const result = await apiCall(`/api/generate/${articleId}`, 'POST', payload);

        if (result.success) {
            showToast(`Blog post created: "${result.post.headline.substring(0, 50)}..."`, 'success');
            setTimeout(() => location.reload(), 1500);
        }
    } catch (error) {
        showToast(`Generation failed: ${error.message}`, 'error');
    }
}


async function publishAll() {
    showToast('🚀 Publishing to WordPress...', 'info');
    // This would publish all draft posts - implemented in a production version
    showToast('Bulk publish is available in the full version', 'info');
}


async function publishToWP(blogId) {
    showToast('🚀 Publishing to WordPress...', 'info');

    try {
        const result = await apiCall(`/api/publish/${blogId}`);

        if (result.success) {
            showToast(`Published! ${result.url || ''}`, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(result.message || 'Publish failed', 'error');
        }
    } catch (error) {
        showToast(`Publish failed: ${error.message}`, 'error');
    }
}


async function exportBlog(blogId) {
    showToast('📄 Exporting HTML...', 'info');

    try {
        const result = await apiCall(`/api/export/${blogId}`);

        if (result.success) {
            showToast(`Exported to: ${result.filepath}`, 'success', 6000);
        }
    } catch (error) {
        showToast(`Export failed: ${error.message}`, 'error');
    }
}


async function runFullPipeline() {
    setButtonLoading('btn-run-all', true);
    showToast('🚀 Running full pipeline...', 'info');

    try {
        // Step 1: Scrape
        showToast('Step 1/2: Scraping news feeds...', 'info');
        const scrapeResult = await apiCall('/api/scrape');

        if (scrapeResult.success) {
            showToast(`Scraped: ${scrapeResult.data.new} new articles`, 'success');
        }

        // Step 2: Generate
        showToast('Step 2/2: Generating blog posts...', 'info');
        const genPayload = { limit: 5 };
        const prompt = getCustomPrompt();
        if (prompt) genPayload.prompt = prompt;
        const genResult = await apiCall('/api/generate', 'POST', genPayload);

        if (genResult.success) {
            showToast(`Pipeline complete! Generated ${genResult.generated} posts.`, 'success', 5000);
        }

        setTimeout(() => location.reload(), 2000);

    } catch (error) {
        showToast(`Pipeline error: ${error.message}`, 'error');
    } finally {
        setButtonLoading('btn-run-all', false);
    }
}


// ===== Scheduler Controls =====

async function toggleScheduler() {
    const btn = document.getElementById('scheduler-toggle-btn');
    const isRunning = btn.classList.contains('btn-danger');

    try {
        if (isRunning) {
            await apiCall('/api/scheduler/stop');
            showToast('Scheduler stopped', 'info');
        } else {
            await apiCall('/api/scheduler/start');
            showToast('Scheduler started! Automation is now active.', 'success');
        }

        setTimeout(() => location.reload(), 1000);
    } catch (error) {
        showToast(`Scheduler error: ${error.message}`, 'error');
    }
}


// ===== CRUD Operations =====

async function deleteArticle(articleId) {
    if (!confirm('Delete this article?')) return;

    try {
        await apiCall(`/api/article/${articleId}/delete`, 'DELETE');
        showToast('Article deleted', 'success');

        const row = document.getElementById(`article-${articleId}`) ||
            document.getElementById(`article-row-${articleId}`);
        if (row) {
            row.style.transition = 'opacity 0.3s, transform 0.3s';
            row.style.opacity = '0';
            row.style.transform = 'translateX(-20px)';
            setTimeout(() => row.remove(), 300);
        }
    } catch (error) {
        showToast(`Delete failed: ${error.message}`, 'error');
    }
}


async function deleteBlog(blogId, redirect = false) {
    if (!confirm('Delete this blog post?')) return;

    try {
        await apiCall(`/api/blog/${blogId}/delete`, 'DELETE');
        showToast('Blog post deleted', 'success');

        if (redirect) {
            setTimeout(() => window.location.href = '/blogs', 1000);
        } else {
            const card = document.getElementById(`blog-card-${blogId}`) ||
                document.getElementById(`blog-row-${blogId}`);
            if (card) {
                card.style.transition = 'opacity 0.3s, transform 0.3s';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.95)';
                setTimeout(() => card.remove(), 300);
            }
        }
    } catch (error) {
        showToast(`Delete failed: ${error.message}`, 'error');
    }
}


// ===== Demo Data =====

async function seedDemo() {
    showToast('🌱 Loading demo data...', 'info');

    try {
        const seedResult = await apiCall('/api/seed-demo');

        if (seedResult.success) {
            showToast(`Loaded ${seedResult.seeded} demo articles!`, 'success');

            // Generate blog posts for demo
            showToast('✨ Generating demo blog posts...', 'info');
            const genResult = await apiCall('/api/generate', 'POST', { limit: 5 });

            if (genResult.success) {
                showToast(`Generated ${genResult.generated} blog posts!`, 'success');
            }

            setTimeout(() => location.reload(), 1500);
        }
    } catch (error) {
        showToast(`Demo data failed: ${error.message}`, 'error');
    }
}


// ===== Mobile Menu =====

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', (e) => {
    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.getElementById('mobile-menu-btn');

    if (sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !menuBtn.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});


// ===== Auto-refresh Stats =====

let refreshInterval = null;

function startAutoRefresh(intervalMs = 30000) {
    if (refreshInterval) clearInterval(refreshInterval);

    refreshInterval = setInterval(async () => {
        try {
            const stats = await apiCall('/api/stats', 'GET');

            const updates = {
                'stat-total-articles': stats.total_articles,
                'stat-unprocessed-count': stats.unprocessed,
                'stat-total-blogs': stats.total_blogs,
                'stat-published-count': stats.published,
            };

            for (const [id, value] of Object.entries(updates)) {
                const el = document.getElementById(id);
                if (el && el.textContent != value) {
                    el.textContent = value;
                    el.style.transition = 'color 0.3s';
                    el.style.color = 'var(--accent-green)';
                    setTimeout(() => el.style.color = '', 1000);
                }
            }
        } catch (e) {
            // Silently fail - user doesn't need to know
        }
    }, intervalMs);
}

// Start auto-refresh if on dashboard
if (window.location.pathname === '/') {
    startAutoRefresh();
}


// ===== Keyboard Shortcuts =====

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + S = Scrape Now
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        scrapeNow();
    }

    // Ctrl/Cmd + G = Generate
    if ((e.ctrlKey || e.metaKey) && e.key === 'g') {
        e.preventDefault();
        generateBlogs();
    }
});
