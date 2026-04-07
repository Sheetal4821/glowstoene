/**
 * Glowstone - Main JavaScript
 * Clean, responsive, performant
 */

document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    // If page loaded with hash (e.g. #collection), show target section and scroll to it
    // (animate-on-scroll starts with opacity:0, so content is invisible until .visible is added)
    function showHashTarget() {
        var hash = window.location.hash;
        if (hash) {
            var target = document.querySelector(hash);
            if (target) {
                var animEls = target.querySelectorAll('.animate-on-scroll');
                if (animEls.length) {
                    animEls.forEach(function(el) { el.classList.add('visible'); });
                } else if (target.classList.contains('animate-on-scroll')) {
                    target.classList.add('visible');
                }
                // Explicitly scroll to target (fixes navigation from other pages)
                requestAnimationFrame(function() {
                    requestAnimationFrame(function() {
                        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    });
                });
            }
        }
    }
    showHashTarget();
    window.addEventListener('hashchange', showHashTarget);
    // Re-scroll on full load (handles layout shift from images when coming from another page)
    if (window.location.hash) {
        window.addEventListener('load', function() {
            var target = document.querySelector(window.location.hash);
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    // Scroll-triggered animations (Intersection Observer)
    const animateElements = document.querySelectorAll('.animate-on-scroll');
    if (animateElements.length > 0) {
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        }, {
            root: null,
            rootMargin: '0px 0px -80px 0px',
            threshold: 0.1
        });
        animateElements.forEach(function(el) { observer.observe(el); });
    }

    // Navbar scroll effect - transparent over first section (hero), solid after (same on all pages)
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        // Detect first section: scroll-driven heroes (#gs-hero, #sus-hero, #care-hero, .inst-step) or page heroes (.about-hero, etc.)
        var heroScrollSection = document.querySelector('#gs-hero, #care-hero, .inst-step');
        var pageHero = document.querySelector('.about-hero, .contact-hero, .faq-hero, .tech-hero, .sh');

        function updateNavbarScroll() {
            var scrollY = window.scrollY || window.pageYOffset;
            var threshold;
            if (heroScrollSection) {
                threshold = heroScrollSection.offsetHeight || window.innerHeight * 5;
            } else if (pageHero) {
                threshold = Math.min(pageHero.offsetHeight || 300, window.innerHeight * 0.8);
            } else {
                threshold = 50;
            }
            navbar.classList.toggle('scrolled', scrollY > threshold);
        }
        var scrollTimeout;
        window.addEventListener('scroll', function() {
            if (scrollTimeout) return;
            scrollTimeout = setTimeout(function() {
                updateNavbarScroll();
                scrollTimeout = null;
            }, 16);
        }, { passive: true });
        window.addEventListener('resize', updateNavbarScroll);
        window.addEventListener('orientationchange', function() {
            setTimeout(updateNavbarScroll, 100);
        });
        updateNavbarScroll();
    }

    // Footer expand/collapse (Caesarstone-style: click + to expand)
    var footerToggle = document.getElementById('footerToggle');
    var footerExpandable = document.querySelector('.footer-expandable');
    if (footerToggle && footerExpandable) {
        function footerNavOffset() {
            var nav = document.querySelector('.navbar.fixed-top');
            var h = nav ? Math.ceil(nav.getBoundingClientRect().height) : 72;
            return h + 12;
        }
        function scrollExpandedFooterIntoView() {
            var footer = document.getElementById('main-footer');
            if (!footer) return;
            var top = footer.getBoundingClientRect().top;
            var offset = footerNavOffset();
            var delta = top - offset;
            if (Math.abs(delta) > 2) {
                window.scrollBy({ top: delta, behavior: 'auto' });
            }
        }
        footerToggle.addEventListener('click', function() {
            var expanded = footerExpandable.classList.toggle('expanded');
            footerToggle.setAttribute('aria-expanded', expanded);
            if (expanded) {
                requestAnimationFrame(function() {
                    requestAnimationFrame(scrollExpandedFooterIntoView);
                });
            }
        });
    }

    // Step 2: Website controls video with scroll (TinyPod-style)
    // Scrolling down → video plays forward | Scrolling up → video reverses
    // Step 3: GSAP ScrollTrigger for smooth sync, pin, and professional feel
    var heroSection = document.querySelector('.hero.hero-scroll-driven');
    var heroWrap = document.querySelector('.hero-video-wrap');
    var heroVideo = document.getElementById('hero-video');

    if (heroSection && heroWrap && heroVideo && typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined' && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        gsap.registerPlugin(ScrollTrigger);

        var scrollVideoInited = false;
        function initScrollVideo() {
            if (scrollVideoInited) return;
            heroVideo.pause();
            var duration = heroVideo.duration;
            if (!duration || !isFinite(duration)) return;
            scrollVideoInited = true;

            ScrollTrigger.create({
                trigger: heroSection,
                start: 'top top',
                end: '+=500%',
                scrub: 1.5,
                pin: true,
                anticipatePin: 1,
                onUpdate: function(self) {
                    var scrollPercent = self.progress;
                    heroVideo.currentTime = scrollPercent * duration;
                    var hint = heroSection.querySelector('.hero-scroll-hint');
                    if (hint) hint.style.opacity = scrollPercent > 0.05 ? Math.max(0, 1 - scrollPercent * 3) : '0.85';
                }
            });
        }

        heroVideo.addEventListener('loadedmetadata', initScrollVideo);
        heroVideo.addEventListener('loadeddata', initScrollVideo);
        heroVideo.addEventListener('canplay', initScrollVideo);
        if (heroVideo.readyState >= 1) initScrollVideo();
    } else if (heroSection && heroVideo && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        // Fallback: vanilla scroll-to-video when GSAP unavailable (Step 2 concept)
        var scrollRange = 3000;
        var ticking = false;
        heroVideo.pause();
        function updateVideoFromScroll() {
            var scrollY = window.scrollY || window.pageYOffset;
            var scrollPercent = Math.min(1, Math.max(0, scrollY / scrollRange));
            if (heroVideo.duration && isFinite(heroVideo.duration)) {
                heroVideo.currentTime = scrollPercent * heroVideo.duration;
            }
            ticking = false;
        }
        heroVideo.addEventListener('loadedmetadata', updateVideoFromScroll);
        window.addEventListener('scroll', function() {
            if (!ticking) {
                requestAnimationFrame(updateVideoFromScroll);
                ticking = true;
            }
        }, { passive: true });
    } else if (heroWrap && !heroSection) {
        var tickingP = false;
        function updateParallax() {
            var scrollY = window.scrollY || window.pageYOffset;
            heroWrap.style.transform = 'translate3d(0, ' + (scrollY * 0.4) + 'px, 0)';
            tickingP = false;
        }
        window.addEventListener('scroll', function() {
            if (!tickingP) { requestAnimationFrame(updateParallax); tickingP = true; }
        }, { passive: true });
        updateParallax();
    }

    // Contact form
    const contactForm = document.getElementById('contactForm');
    const messageInput = document.getElementById('message');
    const charCount = document.querySelector('.char-count');

    if (messageInput && charCount) {
        var maxLen = messageInput.getAttribute('maxlength') || 200;
        messageInput.addEventListener('input', function() {
            charCount.textContent = this.value.length + ' / ' + maxLen + ' characters';
        });
    }

    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            alert('Thank you for your message! We will get back to you soon.');
            this.reset();
            if (charCount) {
                charCount.textContent = '0 / ' + maxLen + ' characters';
            }
        });
    }

    // Close mobile menu when clicking a nav link (smooth UX on mobile)
    document.querySelectorAll('.nav-link').forEach(function(link) {
        link.addEventListener('click', function() {
            var collapse = document.querySelector('.navbar-collapse');
            if (collapse && collapse.classList.contains('show')) {
                var toggle = document.querySelector('.navbar-toggler');
                if (toggle) toggle.click();
            }
        });
    });

    // Hero video - smooth playback (skip for scroll-driven hero, which uses scrub)
    var heroVideoEl = document.querySelector('.hero-video-element');
    var isScrollDriven = !!document.querySelector('.hero.hero-scroll-driven');
    if (heroVideoEl && !isScrollDriven && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        heroVideoEl.play().catch(function() {});
        heroVideoEl.addEventListener('loadeddata', function() {
            heroVideoEl.play().catch(function() {});
        });
    }

    // Image lightbox (product renders + Care & Maintenance + product slab hero) — full size, prev/next carousel
    (function initImageCarouselLightbox() {
        var productItems = document.querySelectorAll('.product-render-item');
        var careItems = document.querySelectorAll('.care-app-lightbox-item');
        var slabImgs = document.querySelectorAll('.product-slab-image img');
        if (productItems.length === 0 && careItems.length === 0 && slabImgs.length === 0) return;

        var lightbox = document.createElement('div');
        lightbox.className = 'render-lightbox';
        lightbox.setAttribute('role', 'dialog');
        lightbox.setAttribute('aria-modal', 'true');
        lightbox.setAttribute('aria-label', 'Image gallery');
        /* Content first so wide centered layer does not paint above nav buttons */
        lightbox.innerHTML = '<div class="render-lightbox-content"></div>' +
            '<button type="button" class="render-lightbox-close" aria-label="Close">&times;</button>' +
            '<button type="button" class="render-lightbox-prev" aria-label="Previous image">&lsaquo;</button>' +
            '<button type="button" class="render-lightbox-next" aria-label="Next image">&rsaquo;</button>' +
            '<span class="render-lightbox-counter"></span>';
        document.body.appendChild(lightbox);

        var closeBtn = lightbox.querySelector('.render-lightbox-close');
        var prevBtn = lightbox.querySelector('.render-lightbox-prev');
        var nextBtn = lightbox.querySelector('.render-lightbox-next');
        var content = lightbox.querySelector('.render-lightbox-content');
        var counter = lightbox.querySelector('.render-lightbox-counter');

        var images = [];
        var currentIndex = 0;
        var carouselWrap = false;

        function openLightbox(index, wrap) {
            carouselWrap = !!wrap;
            currentIndex = index;
            updateLightbox();
            lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
            closeBtn.focus();
        }

        function closeLightbox() {
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
        }

        function updateLightbox() {
            var img = images[currentIndex];
            if (!img) return;
            content.innerHTML = '';
            var full = document.createElement('img');
            full.src = img.src;
            full.alt = img.alt || 'Image';
            content.appendChild(full);
            counter.textContent = (currentIndex + 1) + ' / ' + images.length;
            var multi = images.length > 1;
            if (carouselWrap) {
                prevBtn.disabled = !multi;
                nextBtn.disabled = !multi;
            } else {
                prevBtn.disabled = !multi || currentIndex === 0;
                nextBtn.disabled = !multi || currentIndex === images.length - 1;
            }
        }

        function goPrev() {
            if (images.length <= 1) return;
            if (carouselWrap) {
                currentIndex = (currentIndex - 1 + images.length) % images.length;
            } else if (currentIndex > 0) {
                currentIndex--;
            }
            updateLightbox();
        }

        function goNext() {
            if (images.length <= 1) return;
            if (carouselWrap) {
                currentIndex = (currentIndex + 1) % images.length;
            } else if (currentIndex < images.length - 1) {
                currentIndex++;
            }
            updateLightbox();
        }

        closeBtn.addEventListener('click', closeLightbox);
        prevBtn.addEventListener('click', goPrev);
        nextBtn.addEventListener('click', goNext);

        lightbox.addEventListener('click', function(e) {
            if (e.target === lightbox) closeLightbox();
        });

        document.addEventListener('keydown', function(e) {
            if (!lightbox.classList.contains('active')) return;
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                closeLightbox();
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                e.stopPropagation();
                goPrev();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                e.stopPropagation();
                goNext();
            }
        }, true);

        function bindGroup(itemSelector, containerSelector, imgSelector, wrapCarousel) {
            document.querySelectorAll(itemSelector).forEach(function(item) {
                var img = item.querySelector('img');
                if (!img) return;
                item.addEventListener('click', function() {
                    var container = item.closest(containerSelector);
                    if (!container) return;
                    images = Array.from(container.querySelectorAll(imgSelector));
                    var triggers = Array.from(container.querySelectorAll(itemSelector));
                    var idx = triggers.indexOf(item);
                    openLightbox(idx >= 0 ? idx : 0, wrapCarousel);
                });
            });
        }

        if (productItems.length) {
            bindGroup('.product-render-item', '.product-renders', '.product-render-item img', false);
        }
        if (careItems.length) {
            bindGroup('.care-app-lightbox-item', '.care-bento-grid', '.care-app-lightbox-item img', true);
        }
        if (slabImgs.length) {
            slabImgs.forEach(function(img) {
                img.addEventListener('click', function(e) {
                    e.stopPropagation();
                    var root = img.closest('.product-slab-image');
                    if (!root) return;
                    images = Array.from(root.querySelectorAll('img'));
                    var idx = images.indexOf(img);
                    openLightbox(idx >= 0 ? idx : 0, images.length > 1);
                });
                if (!img.closest('a')) {
                    img.setAttribute('tabindex', '0');
                    img.setAttribute('role', 'button');
                    var baseAlt = img.getAttribute('alt') || 'Slab image';
                    img.setAttribute('aria-label', baseAlt + ', view full size');
                }
                img.addEventListener('keydown', function(e) {
                    if (e.key !== 'Enter' && e.key !== ' ') return;
                    e.preventDefault();
                    img.click();
                });
            });
        }
    })();

});
