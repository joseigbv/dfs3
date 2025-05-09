import { sha512 } from 'https://esm.sh/@noble/hashes/sha512';
import { getPublicKey, utils, etc } from 'https://esm.sh/@noble/ed25519';
import { DFS3_USERS, encryptPrivateKey, bufferToBase64, sha256Hex } from './common.js';

// Error: etc.sha512Sync not set
etc.sha512Sync = sha512;


// ---
// mock api para pruebas
// ---
/*
const originalFetch = window.fetch;

window.fetch = async (url, options) => {
  if (url.endsWith('/api/v1/auth/register')) {
    console.log('[MOCK] POST /auth/register', options.body);
    return new Response(JSON.stringify({ user_id: '01234abcd...' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Resto de fetchs sin cambios
  return originalFetch(url, options);
};
*/


// ---
// Genera claves y devuelve ambas
// ---
async function generateKeys(password) {
  const privateKey = utils.randomPrivateKey();
  const publicKey = await getPublicKey(privateKey);
  return { publicKey, privateKey };
}


// ---
// Guarda claves en localStorage
// ---
async function saveUserKeysToStorage(userId, alias, publicKey, privateKey, password) {
  // Ciframos la clave privada
  const { encryptedPrivateKey, salt, iv } = await encryptPrivateKey(privateKey, password);

  // Existen claves previas? añadimos
  const users = JSON.parse(localStorage.getItem(DFS3_USERS) || '{}');
  users[userId] = {
    alias: alias, 
    public_key: bufferToBase64(publicKey),
    encrypted_private_key: bufferToBase64(encryptedPrivateKey),
    salt: bufferToBase64(salt),
    iv: bufferToBase64(iv)
  };

  // Almacenamos en navegador
  localStorage.setItem(DFS3_USERS, JSON.stringify(users));
}


// ---
// main
// ---

$(function () {
  const $error = $('#error-msg');
  const $output = $('#output');

  // Activación de btn si introducida password
  $('#register-btn').prop('disabled', true);
  $('#alias').on('input', function () {
    $('#register-btn').prop('disabled', $(this).val().trim().length == 0);
  });


  // ---
  // Click register-btn
  // ---
  $('#register-btn').on('click', async () => {
    $error.text('');
    $output.text('');

    const alias = $('#alias').val()?.trim();
    const fullname = $('#fullname').val()?.trim();
    const email = $('#email').val()?.trim();
    const pass1 = $('#password1').val();
    const pass2 = $('#password2').val();

    if (pass1 !== pass2) {
      $error.text('Las contraseñas no coinciden.');
      return;
    }

    if (!alias || !pass1) {
      $error.text('Completar los campos obligatorios.');
      return;
    }

    try {
      const { publicKey, privateKey } = await generateKeys(pass1);
      const userId = await sha256Hex(publicKey);

      // Guarda la clave privada cifrada en localStorage
      await saveUserKeysToStorage(userId, alias, publicKey, privateKey, pass1);

      // Muestra lo que se enviaría al servidor
      const user = {
        user_id: userId,
        alias,
        name: fullname,
        email,
        public_key: bufferToBase64(publicKey)
      };

      console.log(JSON.stringify(user, null, 2));

      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user)
      });

      if (response.ok) {
        $('output').text('Usuario registrado con exito, redirigiendo...');
        window.location.href = 'index.html';

      } else {
        const e = await response.text();
        throw new Error(e);
      }

    } catch (e) {
      $error.text('Error durante el registro.');
      console.log(e);
    }

  });
});
