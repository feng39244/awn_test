// Translations object (example, replace with your actual translations)
const translations = {
  en: {
    alertSyncSuccess: "Calendar synced successfully!",
    alertBilledSuccess: "Patient marked as billed.",
    placeholderName: "Enter name",
    placeholderEmail: "Enter email",
  },
  zh: {
    alertSyncSuccess: "日历同步成功！",
    alertBilledSuccess: "病人已标记为已计费。",
    placeholderName: "输入名字",
    placeholderEmail: "输入电子邮件",
  },
}

// Current language
let currentLang = "en"

// Function to toggle language
function toggleLanguage() {
  currentLang = document.getElementById("languageSwitch").checked ? "zh" : "en"
  updateLanguage()

  // Save language preference
  localStorage.setItem("preferredLanguage", currentLang)
}

// Function to update language on the page
function updateLanguage() {
  // Update elements with data-i18n attribute
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.getAttribute("data-i18n")
    if (translations[currentLang][key]) {
      element.textContent = translations[currentLang][key]
    }
  })

  // Update placeholders
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    const key = element.getAttribute("data-i18n-placeholder")
    if (translations[currentLang][key]) {
      element.placeholder = translations[currentLang][key]
    }
  })

  // Update document language
  document.documentElement.lang = currentLang
}

// Initialize language from saved preference
document.addEventListener("DOMContentLoaded", () => {
  const savedLang = localStorage.getItem("preferredLanguage")
  if (savedLang) {
    currentLang = savedLang
    document.getElementById("languageSwitch").checked = currentLang === "zh"
    updateLanguage()
  }
})

// Function to simulate calendar sync
function simulateSync(type) {
  const btnId = type === "calendar" ? "sync-calendar-btn" : "sync-auth-btn"
  const iconId = type === "calendar" ? "sync-calendar-icon" : "sync-auth-icon"

  const syncBtn = document.getElementById(btnId)
  const syncIcon = document.getElementById(iconId)

  // Disable button and show spinner
  syncBtn.disabled = true
  syncIcon.classList.add("bi-arrow-repeat")
  syncIcon.classList.add("rotate")
  syncIcon.classList.remove("bi-calendar-check")

  // Simulate API call
  setTimeout(() => {
    showAlert("success", translations[currentLang].alertSyncSuccess)

    // Reset button
    syncBtn.disabled = false
    syncIcon.classList.remove("bi-arrow-repeat")
    syncIcon.classList.remove("rotate")
    syncIcon.classList.add("bi-calendar-check")
  }, 1500)
}

// Function to mark patient as billed
function markAsBilled(patientId) {
  // Remove patient row from table
  const row = document.getElementById(`patient-row-${patientId}`)
  if (row) {
    row.remove()
  }

  showAlert("success", translations[currentLang].alertBilledSuccess)
}

// Function to show alert
function showAlert(type, message) {
  const alertContainer = document.getElementById("alert-container")
  const alert = document.createElement("div")
  alert.className = `alert alert-${type} alert-dismissible fade show`
  alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `
  alertContainer.appendChild(alert)

  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    alert.classList.remove("show")
    setTimeout(() => {
      alertContainer.removeChild(alert)
    }, 150)
  }, 5000)
}

