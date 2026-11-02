import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { chinese } from './locales/zh-CN'

export const languageStorageKey = 'dayloom.language'
export const languages = [
  { value: 'en', label: 'English' },
  { value: 'zh-CN', label: '简体中文' },
] as const

function initialLanguage() {
  try {
    const saved = localStorage.getItem(languageStorageKey)
    if (languages.some((language) => language.value === saved)) return saved!
  } catch {}
  return navigator.language.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en'
}

void i18n.use(initReactI18next).init({
  lng: initialLanguage(),
  fallbackLng: 'en',
  supportedLngs: languages.map((language) => language.value),
  keySeparator: false,
  nsSeparator: false,
  resources: { en: { translation: {} }, 'zh-CN': { translation: chinese } },
  interpolation: { escapeValue: false },
})

function updateDocument(language: string) {
  document.documentElement.lang = language
  document.title = i18n.t('Dayloom | Your Personal Workspace')
  try {
    localStorage.setItem(languageStorageKey, language)
  } catch {
    return
  }
}

updateDocument(i18n.language)
i18n.on('languageChanged', updateDocument)

export default i18n
