import { Languages } from 'lucide-react'
import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { languages } from '../i18n'

export function LanguagePicker() {
  const { t, i18n } = useTranslation()
  const fieldId = useId()
  return (
    <div className="language-picker">
      <label htmlFor={fieldId}>
        <Languages size={16} aria-hidden="true" /> {t('Language')}
      </label>
      <select
        id={fieldId}
        value={i18n.language}
        onChange={(event) => void i18n.changeLanguage(event.target.value)}
      >
        {languages.map((language) => (
          <option key={language.value} value={language.value}>
            {language.label}
          </option>
        ))}
      </select>
    </div>
  )
}
