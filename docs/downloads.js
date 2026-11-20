(async function () {
  const androidStatus = document.getElementById('android-download-status');
  let manifest;
  try {
    const response = await fetch('update-manifest.json');
    if (response.ok) manifest = await response.json();
  } catch {
    // The desktop links in the HTML also work when the manifest is unavailable.
  }
  if (!manifest) {
    androidStatus.textContent = 'APK availability could not be checked.';
    return;
  }

  function releaseUrl(entry, extension) {
    if (typeof entry?.url !== 'string') return null;
    try {
      const url = new URL(entry.url);
      return url.protocol === 'https:' && url.pathname.toLowerCase().endsWith(extension) ? url : null;
    } catch {
      return null;
    }
  }

  for (const platform of ['windows', 'linux']) {
    const url = releaseUrl(manifest.platforms?.[platform], '.zip');
    if (url) {
      document.getElementById('download-' + platform).href = url.href;
    }
  }

  function releaseApk(entry) {
    const url = releaseUrl(entry, '.apk');
    return url && !/[-/_.](debug|unsigned)[-/_.]/i.test(url.pathname) ? url : null;
  }

  let apk = releaseApk(manifest.platforms?.android);
  if (!apk && Array.isArray(manifest.assets)) {
    const apks = manifest.assets.map(releaseApk).filter(Boolean);
    // Prefer the published companion filename when a release includes multiple APKs.
    apk = apks.length === 1 ? apks[0] : apks.find(url => url.pathname.toLowerCase().endsWith('/stashsageandroid.apk'));
  }
  if (apk) {
    const link = document.createElement('a');
    link.className = 'btn';
    link.href = apk.href;
    link.textContent = 'Download for Android (.apk)';
    androidStatus.replaceWith(link);
  }
})();
