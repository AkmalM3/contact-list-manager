import pytest
from app import app, db
from models import Contact

@pytest.fixture
def client():
    # Configure app for testing
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing

    # Create test client
    with app.test_client() as client:
        with app.app_context():
            # Create all tables in the test database
            db.create_all()
            yield client
            # Clean up after tests
            db.session.remove()
            db.drop_all()

@pytest.fixture
def sample_contact():
    contact = Contact(
        name='John Doe',
        phone='1234567890',
        email='john@example.com',
        type='Personal'
    )
    db.session.add(contact)
    db.session.commit()
    return contact

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200

def test_add_contact(client):
    data = {
        'name': 'Jane Doe',
        'phone': '9876543210',
        'email': 'jane@example.com',
        'type': 'Personal'
    }
    response = client.post('/add', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Jane Doe' in response.data

def test_update_contact(client, sample_contact):
    data = {
        'name': 'John Smith',
        'phone': sample_contact.phone,
        'email': sample_contact.email,
        'type': sample_contact.type,
        'submit': 'Update'
    }
    response = client.post(
        f'/update/{sample_contact.id}',
        data=data,
        follow_redirects=True
    )
    assert response.status_code == 200
    updated_contact = db.session.get(Contact, sample_contact.id)
    assert updated_contact.name == 'John Smith'

def test_delete_contact(client, sample_contact):
    # Ensure the contact is in the database before deletion
    contact_in_db = db.session.get(Contact, sample_contact.id)
    assert contact_in_db is not None

    # Send DELETE request to delete the contact
    response = client.get(f'/delete/{sample_contact.id}', follow_redirects=True)

    # Check if the contact is deleted by verifying that the response status is 200
    # and the contact is no longer in the database
    assert response.status_code == 200

    contact_in_db_after_deletion = db.session.get(Contact, sample_contact.id)
    assert contact_in_db_after_deletion is None

def test_update_contact_invalid_data(client, sample_contact):
    # Prepare invalid data (empty name)
    data = {
        'name': '',
        'phone': sample_contact.phone,
        'email': sample_contact.email,
        'type': sample_contact.type
    }

    # Send POST request to update the contact with invalid data
    response = client.post(f'/update/{sample_contact.id}', data=data, follow_redirects=True)

    # Check if the response status is 200 (the page should reload with validation errors)
    assert response.status_code == 200

    # Ensure the contact's name is still the original (i.e., it wasn't updated)
    contact_in_db = db.session.get(Contact, sample_contact.id)
    assert contact_in_db.name == sample_contact.name
def test_get_contacts_api(client, sample_contact):
    response = client.get('/api/contacts')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['name'] == 'John Doe'

def test_get_single_contact_api(client, sample_contact):
    response = client.get(f'/api/contacts/{sample_contact.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'John Doe'

def test_create_contact_api(client):
    data = {
        'name': 'API User',
        'phone': '5555555555',
        'email': 'api@example.com',
        'type': 'work'
    }
    response = client.post('/api/contacts', json=data)
    assert response.status_code == 201
    assert response.get_json()['name'] == 'API User'

def test_update_contact_api(client, sample_contact):
    data = {
        'name': 'Updated API User',
        'phone': '5555551234',
        'email': 'updated_api@example.com',
        'type': 'personal'
    }
    
    # Send PUT request to update the contact via API
    response = client.put(f'/api/contacts/{sample_contact.id}', json=data)
    
    assert response.status_code == 200
    updated_contact = response.get_json()
    
    # Check if the contact was updated correctly
    assert updated_contact['name'] == 'Updated API User'
    assert updated_contact['phone'] == '5555551234'
    assert updated_contact['email'] == 'updated_api@example.com'
    assert updated_contact['type'] == 'personal'

def test_delete_contact_api(client, sample_contact):
    # Send DELETE request to delete the contact via API
    response = client.delete(f'/api/contacts/{sample_contact.id}')
    
    assert response.status_code == 204  # No content on successful deletion

    # Try to get the deleted contact, it should return 404
    response = client.get(f'/api/contacts/{sample_contact.id}')
    assert response.status_code == 404

def test_list_contact_api(client, sample_contact):
    # Send GET request to fetch all contacts via the API
    response = client.get('/api/contacts')
    
    assert response.status_code == 200
    data = response.get_json()
    
    # Check if the response contains the sample contact data
    assert len(data) > 0  # Make sure there's at least one contact
    assert any(contact['name'] == 'John Doe' for contact in data)

# Test error cases
def test_invalid_contact_creation(client):
    data = {
        'name': 'Invalid User',
        # Missing required fields
    }
    response = client.post('/api/contacts', json=data)
    assert response.status_code == 400

def test_get_nonexistent_contact(client):
    response = client.get('/api/contacts/999')
    assert response.status_code == 404 