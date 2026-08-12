"use strict";

/**
 * Client-side form validation for settings and auth forms.
 */
(function initValidators(global) {
  const URL_RE = /^https?:\/\/.+/i;

  function validateUrl(value, label) {
    const trimmed = String(value || "").trim();
    if (!URL_RE.test(trimmed)) {
      return `${label} must start with http:// or https://`;
    }
    return null;
  }

  function validateTemperature(value) {
    const num = Number(value);
    if (Number.isNaN(num) || num < 0 || num > 2) {
      return "temperature must be between 0 and 2";
    }
    return null;
  }

  function validateMessage(value) {
    const trimmed = String(value || "").trim();
    if (!trimmed) {
      return "message cannot be empty";
    }
    if (trimmed.length > 20000) {
      return "message is too long";
    }
    return null;
  }

  function validateSettings(payload) {
    const errors = [];
    if (payload.ollama_url) {
      const err = validateUrl(payload.ollama_url, "Ollama endpoint");
      if (err) errors.push(err);
    }
    if (payload.voice_url) {
      const err = validateUrl(payload.voice_url, "Voice bridge URL");
      if (err) errors.push(err);
    }
    if (payload.temperature !== undefined) {
      const err = validateTemperature(payload.temperature);
      if (err) errors.push(err);
    }
    return errors;
  }

  function validateAuth(email, password) {
    const errors = [];
    if (!String(email || "").includes("@")) {
      errors.push("valid email required");
    }
    if (String(password || "").length < 8) {
      errors.push("password must be at least 8 characters");
    }
    if (new TextEncoder().encode(String(password || "")).length > 72) {
      errors.push("password must be at most 72 UTF-8 bytes");
    }
    return errors;
  }

  global.AnnieValidators = {
    validateUrl,
    validateTemperature,
    validateMessage,
    validateSettings,
    validateAuth,
  };
})(window);
