import test from 'node:test'
import assert from 'node:assert/strict'
import { credentialError } from '../src/utils/recovery.js'

test('tracking accepts a full secret and rejects account names and request numbers', () => {
    assert.equal(credentialError('a'.repeat(43)), '')
    assert.equal(credentialError('  '+ 'a'.repeat(43) +'  '), '')
    for (const value of ['reader','LF-00000001','a'.repeat(42),'a'.repeat(44),'='.repeat(43)]) assert.notEqual(credentialError(value),'')
})

