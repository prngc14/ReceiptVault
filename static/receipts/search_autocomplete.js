(() => {
    const script = document.currentScript;
    const suggestionsUrl = script.dataset.suggestionsUrl;
    const forms = document.querySelectorAll('form');

    forms.forEach((form) => {
        const input = form.querySelector('input[name="q"]');
        if (!input) {
            return;
        }

        const dropdown = document.createElement('div');
        dropdown.className = 'receipt-search-suggestions';
        dropdown.setAttribute('role', 'listbox');
        dropdown.hidden = true;
        form.appendChild(dropdown);
        form.style.position = 'relative';
        input.setAttribute('aria-autocomplete', 'list');
        input.setAttribute('aria-expanded', 'false');

        let debounceTimer;
        let activeRequest;
        let requestId = 0;

        const hideSuggestions = () => {
            dropdown.hidden = true;
            input.setAttribute('aria-expanded', 'false');
        };

        const addGroup = (title, items) => {
            if (!items.length) {
                return;
            }

            const group = document.createElement('div');
            group.className = 'receipt-search-suggestions__group';

            const heading = document.createElement('div');
            heading.className = 'receipt-search-suggestions__heading';
            heading.textContent = title;
            group.appendChild(heading);

            items.forEach((item) => {
                const link = document.createElement('a');
                link.className = 'receipt-search-suggestions__item';
                link.href = item.url;
                link.setAttribute('role', 'option');
                link.textContent = item.name;

                if (item.detail) {
                    const detail = document.createElement('span');
                    detail.className = 'receipt-search-suggestions__detail';
                    detail.textContent = item.detail;
                    link.appendChild(detail);
                }

                group.appendChild(link);
            });

            dropdown.appendChild(group);
        };

        input.addEventListener('input', () => {
            window.clearTimeout(debounceTimer);
            if (activeRequest) {
                activeRequest.abort();
                activeRequest = null;
            }

            const query = input.value.trim();
            const currentRequestId = ++requestId;
            if (query.length < 2) {
                hideSuggestions();
                return;
            }

            debounceTimer = window.setTimeout(async () => {
                activeRequest = new AbortController();

                try {
                    const url = new URL(suggestionsUrl, window.location.origin);
                    url.searchParams.set('q', query);
                    const response = await fetch(url, {
                        signal: activeRequest.signal,
                        headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    });
                    if (!response.ok) {
                        throw new Error(`Suggestion request failed: ${response.status}`);
                    }

                    const data = await response.json();
                    if (currentRequestId !== requestId) {
                        return;
                    }

                    dropdown.replaceChildren();
                    addGroup('Companies', data.companies);
                    addGroup('Receipts', data.receipts);
                    const hasSuggestions = dropdown.childElementCount > 0;
                    dropdown.hidden = !hasSuggestions;
                    input.setAttribute('aria-expanded', String(hasSuggestions));
                } catch (error) {
                    if (error.name !== 'AbortError') {
                        console.error('Could not load search suggestions.', error);
                        hideSuggestions();
                    }
                }
            }, 250);
        });

        input.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                hideSuggestions();
            }
        });

        document.addEventListener('click', (event) => {
            if (!form.contains(event.target)) {
                hideSuggestions();
            }
        });
    });
})();
