/**
 * API Response Validator
 * Utility functions to validate API responses against the defined templates
 */

const templates = require('./frontend-response-templates');

// Validation utilities
class APIResponseValidator {
  /**
   * Validate if an object matches the expected structure
   * @param {Object} obj - Object to validate
   * @param {Object} template - Template to validate against
   * @param {boolean} strict - Whether to enforce strict validation
   * @returns {Object} Validation result
   */
  static validateStructure(obj, template, strict = false) {
    const errors = [];
    const warnings = [];

    if (!obj || typeof obj !== 'object') {
      errors.push('Object is null or not an object');
      return { isValid: false, errors, warnings };
    }

    // Check required fields
    for (const [key, expectedValue] of Object.entries(template)) {
      if (!(key in obj)) {
        if (this.isRequiredField(template, key)) {
          errors.push(`Missing required field: ${key}`);
        } else {
          warnings.push(`Optional field missing: ${key}`);
        }
      } else {
        const actualValue = obj[key];
        const typeError = this.validateFieldType(key, actualValue, expectedValue);
        if (typeError) {
          errors.push(typeError);
        }
      }
    }

    // Check for extra fields in strict mode
    if (strict) {
      for (const key in obj) {
        if (!(key in template)) {
          warnings.push(`Unexpected field: ${key}`);
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Check if a field is required based on template
   * @private
   */
  static isRequiredField(template, field) {
    // Simple heuristic: if the template value is not null/undefined, consider it required
    // In a real implementation, you'd use schema metadata
    const value = template[field];
    return value !== null && value !== undefined;
  }

  /**
   * Validate field type
   * @private
   */
  static validateFieldType(fieldName, actualValue, expectedValue) {
    const actualType = typeof actualValue;
    const expectedType = typeof expectedValue;

    // Handle null values (nullable fields)
    if (actualValue === null) {
      return null; // null is acceptable for nullable fields
    }

    // Type validation
    if (actualType !== expectedType) {
      // Allow some type flexibility
      if (expectedType === 'number' && actualType === 'string' && !isNaN(actualValue)) {
        return null; // String numbers are acceptable
      }
      if (expectedType === 'string' && actualType === 'number') {
        return null; // Number strings are acceptable
      }
      return `Field '${fieldName}' type mismatch: expected ${expectedType}, got ${actualType}`;
    }

    // Array validation
    if (Array.isArray(expectedValue) && Array.isArray(actualValue)) {
      // Could add deeper array validation here
      return null;
    }

    // Object validation (recursive)
    if (expectedType === 'object' && actualType === 'object' && expectedValue && !Array.isArray(expectedValue)) {
      const nestedValidation = this.validateStructure(actualValue, expectedValue, false);
      if (!nestedValidation.isValid) {
        return `Field '${fieldName}' has invalid structure: ${nestedValidation.errors.join(', ')}`;
      }
    }

    return null;
  }

  /**
   * Validate a UserProfile response
   */
  static validateUserProfile(response) {
    return this.validateStructure(response, templates.UserProfile);
  }

  /**
   * Validate a Torrent response
   */
  static validateTorrent(response) {
    return this.validateStructure(response, templates.Torrent);
  }

  /**
   * Validate a paginated response
   */
  static validatePaginatedResponse(response, itemTemplate) {
    const paginationValidation = this.validateStructure(response, templates.PaginatedResponseTemplate);

    if (!paginationValidation.isValid) {
      return paginationValidation;
    }

    // Validate each item in results array
    const itemErrors = [];
    if (Array.isArray(response.results)) {
      response.results.forEach((item, index) => {
        const itemValidation = this.validateStructure(item, itemTemplate);
        if (!itemValidation.isValid) {
          itemErrors.push(`Item ${index}: ${itemValidation.errors.join(', ')}`);
        }
      });
    }

    return {
      isValid: paginationValidation.isValid && itemErrors.length === 0,
      errors: [...paginationValidation.errors, ...itemErrors],
      warnings: paginationValidation.warnings
    };
  }

  /**
   * Validate a CreditTransaction response
   */
  static validateCreditTransaction(response) {
    return this.validateStructure(response, templates.CreditTransaction);
  }

  /**
   * Validate an Alert response
   */
  static validateAlert(response) {
    return this.validateStructure(response, templates.Alert);
  }

  /**
   * Validate API error response
   */
  static validateAPIError(error) {
    return templates.isAPIError(error);
  }

  /**
   * Comprehensive validation report
   */
  static generateValidationReport(response, expectedType) {
    let validation;

    switch (expectedType) {
      case 'UserProfile':
        validation = this.validateUserProfile(response);
        break;
      case 'Torrent':
        validation = this.validateTorrent(response);
        break;
      case 'CreditTransaction':
        validation = this.validateCreditTransaction(response);
        break;
      case 'Alert':
        validation = this.validateAlert(response);
        break;
      case 'PaginatedTorrents':
        validation = this.validatePaginatedResponse(response, templates.Torrent);
        break;
      case 'PaginatedUserManagement':
        validation = this.validatePaginatedResponse(response, templates.UserManagement);
        break;
      default:
        return {
          isValid: false,
          errors: [`Unknown validation type: ${expectedType}`],
          warnings: []
        };
    }

    return {
      type: expectedType,
      timestamp: new Date().toISOString(),
      ...validation
    };
  }
}

// Export validation utilities
module.exports = {
  APIResponseValidator,
  validateUserProfile: (response) => APIResponseValidator.validateUserProfile(response),
  validateTorrent: (response) => APIResponseValidator.validateTorrent(response),
  validatePaginatedResponse: (response, itemTemplate) => APIResponseValidator.validatePaginatedResponse(response, itemTemplate),
  validateAPIError: (error) => APIResponseValidator.validateAPIError(error),
  generateValidationReport: (response, type) => APIResponseValidator.generateValidationReport(response, type)
};

// Example usage:
/*
const validator = require('./api-response-validator');

try {
  const response = await api.get('/api/user/profile/');
  const validation = validator.validateUserProfile(response.data);

  if (!validation.isValid) {
    console.error('API Response validation failed:', validation.errors);
  } else {
    console.log('Response is valid!');
  }
} catch (error) {
  console.error('API call failed:', error);
}
*/
